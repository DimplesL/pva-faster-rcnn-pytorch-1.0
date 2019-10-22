import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from .basic_modules import initvars
from tools.checkpoint import load_checkpoint


# XXX: Not tested
class CReLU(nn.Module):
    def __init__(self, act=F.relu):
        super(CReLU, self).__init__()

        self.act = act

    def forward(self, x):
        x = torch.cat((x, -x), 1)
        x = self.act(x)

        return x


class ConvBnAct(nn.Module):
    def __init__(self, n_in, n_out, **kwargs):
        super(ConvBnAct, self).__init__()

        self.conv = nn.Conv2d(n_in, n_out, bias=False, **kwargs)
        self.bn = nn.BatchNorm2d(n_out)
        self.act = F.relu

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.act(x)

        return x


class mCReLU_base(nn.Module):
    def __init__(self, n_in, n_out, kernelsize, stride=1, preAct=False, lastAct=True):
        super(mCReLU_base, self).__init__()
        # Config
        self._preAct = preAct
        self._lastAct = lastAct
        self.act = F.relu

        # Trainable params
        self.conv3x3 = nn.Conv2d(n_in, n_out, kernelsize, stride=stride, padding=int(kernelsize / 2))
        self.bn = nn.BatchNorm2d(n_out * 2)

    def forward(self, x):
        if self._preAct:
            x = self.act(x)

        # Conv 3x3 - mCReLU (w/ BN)
        x = self.conv3x3(x)
        x = torch.cat((x, -x), 1)
        x = self.bn(x)

        # TODO: Add scale-bias layer and make 'bn' optional

        if self._lastAct:
            x = self.act(x)

        return x


class mCReLU_residual(nn.Module):
    def __init__(self, n_in, n_red, n_3x3, n_out, kernelsize=3, in_stride=1, proj=False, preAct=False, lastAct=True):
        super(mCReLU_residual, self).__init__()
        # Config
        self._preAct = preAct
        self._lastAct = lastAct
        self._stride = in_stride
        self.act = F.relu

        # Trainable params
        self.reduce = nn.Conv2d(n_in, n_red, 1, stride=in_stride)
        self.conv3x3 = nn.Conv2d(n_red, n_3x3, kernelsize, padding=int(kernelsize / 2))
        self.bn = nn.BatchNorm2d(n_3x3 * 2)
        self.expand = nn.Conv2d(n_3x3 * 2, n_out, 1)

        if in_stride > 1:
            # TODO: remove this assertion
            assert (proj)

        self.proj = nn.Conv2d(n_in, n_out, 1, stride=in_stride) if proj else None

    def forward(self, x):
        x_sc = x

        if self._preAct:
            x = self.act(x)

        # Conv 1x1 - Relu
        x = self.reduce(x)
        x = self.act(x)

        # Conv 3x3 - mCReLU (w/ BN)
        x = self.conv3x3(x)
        x = torch.cat((x, -x), 1)
        x = self.bn(x)
        x = self.act(x)

        # TODO: Add scale-bias layer and make 'bn' optional

        # Conv 1x1
        x = self.expand(x)

        if self._lastAct:
            x = self.act(x)

        # Projection
        if self.proj:
            x_sc = self.proj(x_sc)

        x = x + x_sc

        return x


class Inception(nn.Module):
    def __init__(self, n_in, n_out, in_stride=1, preAct=False, lastAct=True, proj=False):
        super(Inception, self).__init__()

        # Config
        self._preAct = preAct
        self._lastAct = lastAct
        self.n_in = n_in
        self.n_out = n_out
        self.act_func = nn.ReLU
        self.act = F.relu
        self.in_stride = in_stride

        self.n_branches = 0
        self.n_outs = []  # number of output feature for each branch

        self.proj = nn.Conv2d(n_in, n_out, 1, stride=in_stride) if proj else None

    def add_branch(self, module, n_out):
        # Create branch
        br_name = 'branch_{}'.format(self.n_branches)
        setattr(self, br_name, module)

        # Last output chns.
        self.n_outs.append(n_out)

        self.n_branches += 1

    def branch(self, idx):
        br_name = 'branch_{}'.format(idx)
        return getattr(self, br_name, None)

    def add_convs(self, n_kernels, n_chns):
        assert (len(n_kernels) == len(n_chns))

        n_last = self.n_in
        layers = []

        stride = -1
        for k, n_out in zip(n_kernels, n_chns):
            if stride == -1:
                stride = self.in_stride
            else:
                stride = 1

            # Initialize params
            conv = nn.Conv2d(n_last, n_out, kernel_size=k, bias=False, padding=int(k / 2), stride=stride)
            bn = nn.BatchNorm2d(n_out)

            # Instantiate network
            layers.append(conv)
            layers.append(bn)
            layers.append(self.act_func())

            n_last = n_out

        self.add_branch(nn.Sequential(*layers), n_last)

        return self

    def add_poolconv(self, kernel, n_out, type='MAX'):

        assert (type in ['AVE', 'MAX'])

        n_last = self.n_in
        layers = []

        # Pooling
        if type == 'MAX':
            layers.append(nn.MaxPool2d(kernel, padding=int(kernel / 2), stride=self.in_stride))
        elif type == 'AVE':
            layers.append(nn.AvgPool2d(kernel, padding=int(kernel / 2), stride=self.in_stride))

        # Conv - BN - Act
        layers.append(nn.Conv2d(n_last, n_out, kernel_size=1))
        layers.append(nn.BatchNorm2d(n_out))
        layers.append(self.act_func())

        self.add_branch(nn.Sequential(*layers), n_out)

        return self

    def finalize(self):
        # Add 1x1 convolution
        total_outs = sum(self.n_outs)

        self.last_conv = nn.Conv2d(total_outs, self.n_out, kernel_size=1)
        self.last_bn = nn.BatchNorm2d(self.n_out)

        return self

    def forward(self, x):
        x_sc = x

        if (self._preAct):
            x = self.act(x)

        # Compute branches
        h = []
        for i in range(self.n_branches):
            module = self.branch(i)
            assert (module != None)

            h.append(module(x))

        x = torch.cat(h, dim=1)

        x = self.last_conv(x)
        x = self.last_bn(x)

        if (self._lastAct):
            x = self.act(x)

        if (x_sc.get_device() != x.get_device()):
            print("Something's wrong")

        # Projection
        if self.proj:
            x_sc = self.proj(x_sc)

        x = x + x_sc

        return x


class pvanet(nn.Module):


    def __init__(self, cfg):
        super(pvanet, self).__init__()
        self.output_feature = cfg.model.network.output_feature
        self.output_feature = cfg.model.network.output_feature
        self.low_level = np.min(np.array(self.output_feature))
        self.high_level = np.max(np.array(self.output_feature))
        self.conv1 = nn.Sequential(
            mCReLU_base(3, 16, kernelsize=3, stride=2, lastAct=False),
            nn.Conv2d(32, 16, kernel_size=1, stride=1),
            nn.Conv2d(16, 16, kernel_size=3, stride=1),
            nn.Conv2d(16, 16, kernel_size=3, stride=1),
            nn.Conv2d(16, 32, kernel_size=1, stride=1),
            nn.MaxPool2d(3, padding=1, stride=2)
        )

        # 1/4
        self.conv2 = nn.Sequential(
            mCReLU_residual(32, 24, 24, 64, kernelsize=3, preAct=True, lastAct=False, in_stride=1, proj=True),
            mCReLU_residual(64, 24, 24, 64, kernelsize=3, preAct=True, lastAct=False),
            mCReLU_residual(64, 24, 24, 64, kernelsize=3, preAct=True, lastAct=False)
        )

        # 1/8
        self.conv3 = nn.Sequential(
            mCReLU_residual(64, 48, 48, 128, kernelsize=3, preAct=True, lastAct=False, in_stride=2, proj=True),
            mCReLU_residual(128, 48, 48, 128, kernelsize=3, preAct=True, lastAct=False),
            mCReLU_residual(128, 48, 48, 128, kernelsize=3, preAct=True, lastAct=False),
            mCReLU_residual(128, 48, 48, 128, kernelsize=3, preAct=True, lastAct=False)
        )

        # 1/16
        self.conv4 = nn.Sequential(
            self.gen_InceptionA(128, 2, True),
        )

        # 1/32
        self.conv5 = nn.Sequential(
            self.gen_InceptionB(256, 2, True),
            nn.ReLU(inplace=True)
        )

        self.downsample1 = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)


    def _init_weights__(self, pretrained=False):

        import os
        if pretrained and os.path.isfile(self.cfg.pretrained):
            load_checkpoint(self, self.cfg.pretrained)
        else:
            initvars(self.modules())


    def forward(self, images):
        x0 = self.conv1(images)
        x1 = self.conv2(x0)  # 1/4  64
        x2 = self.conv3(x1)  # 1/8  128
        x3 = self.conv4(x2)  # 1/16 256
        x4 = self.conv5(x3)  # 1/32 384

        all_features = [x1, x2, x3, x4]

        return all_features[self.low_level:self.high_level+1]


    def gen_InceptionA(self, n_in, stride=1, poolconv=False, n_out=256):
        if (n_in != n_out) or (stride > 1):
            proj = True
        else:
            proj = False

        module = Inception(n_in, n_out, preAct=True, lastAct=False, in_stride=stride, proj=proj) \
            .add_convs([1], [64]) \
            .add_convs([1, 3], [48, 128]) \
            .add_convs([1, 3, 3], [24, 48, 48])

        if poolconv:
            module.add_poolconv(3, 128)

        return module.finalize()


    def gen_InceptionB(self, n_in, stride=1, poolconv=False, n_out=384):
        if (n_in != n_out) or (stride > 1):
            proj = True
        else:
            proj = False

        module = Inception(n_in, n_out, preAct=True, lastAct=False, in_stride=stride, proj=proj) \
            .add_convs([1], [64]) \
            .add_convs([1, 3], [96, 192]) \
            .add_convs([1, 3, 3], [32, 64, 64])

        if poolconv:
            module.add_poolconv(3, 128)

        return module.finalize()


def get_model(output_feature, pretrained):
    model = pvanet(output_feature, pretrained)
    return model