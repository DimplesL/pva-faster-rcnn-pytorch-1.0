model_cfg = dict(
    class_list=('__background__',
                'SLD', 'SQ', 'KP', 'WQ', 'YHS', 'SL', 'SLK', 'SLL', 'FC', 'JD', 'SX', 'KQ', 'WC',
                'ZF', 'DJ', 'JG', 'MK'),
    defect_class_list=('SLD', 'SQ', 'KP', 'WQ', 'YHS', 'SL', 'SLK', 'SLL'),
    rename_class_list={
        'DJ': ['DJ', 'CD', 'CJ', 'KT'],
        'JG': ['JG', 'KZ', 'LS', 'SH', 'RK', 'HD'],
        'KP': ['KP1'],
    },
    confidence_per_cls={'SLD': [0.79], 'SQ': [0.75], 'KP': [0.87], 'WQ': [0.8], 'YHS': [0.84], 'SL': [0.89], 'SLK': [0.84], 'SLL': [
        0.89], 'FC': [0.75], 'JD': [0.98], 'SX': [0.99], 'KQ': [0.99], 'WC': [0.99], 'ZF': [0.98], 'DJ': [0.99], 'JG': [0.95], 'MK': [0.8]},
    ANCHOR_SCALES=[1.2, 2.5, 6, 10, 14, 20, 40],
    #ANCHOR_SCALES=[0.5, 1.2, 2.5, 6, 10, 14, 20, 40],
    ANCHOR_RATIOS=[0.333, 0.5, 0.667, 1, 1.5, 2, 3],
    #ANCHOR_RATIOS=[0.167, 0.333, 0.5, 0.667, 1, 1.5, 2, 3],
    POOLING_MODE='align',
    POOLING_SIZE=7,
    FEAT_STRIDE=[8],

    model="save_models/vertical_defect_0812_0872.ckpt",  # save_models
    save_model_interval=1,

    MODEL=dict(
        RCNN_CIN=512,
        RPN_CIN=512,
        RCNN_LAST=512,
        BACKBONE='shortlitehyper',
        DOUT_BASE_MODEL=336,
    ),

    TRAIN=dict(
        dataset="xml",
        train_path="/data0/datasets/det_vertical_defect/2/original",
        val_path=None,
        save_dir="save_models/",
        # resume_model=None,
        resume_model="save_models/vertical_defect_0812_0230.ckpt",  # 0812_0872.ckpt
        model_name="vertical_defect_0812_",
        gpus=(2, 3),
        batch_size_per_gpu=64,
        epochs=1000,
        num_works=0,
        loss_type="smoothL1loss",  # "smoothL1loss" "GIOUloss" "IOUloss"
        LEARNING_RATE=0.0001,
        MOMENTUM=0.9,
        WEIGHT_DECAY=0.0005,
        BATCH_SIZE=128,
        FG_FRACTION=0.25,
        FG_THRESH=0.5,
        BG_THRESH_HI=0.5,
        BG_THRESH_LO=0.0,
        RPN_POSITIVE_OVERLAP=0.7,
        RPN_NEGATIVE_OVERLAP=0.3,
        RPN_FG_FRACTION=0.5,
        RPN_BATCHSIZE=256,
        RPN_NMS_THRESH=0.7,
        RPN_PRE_NMS_TOP_N=12000,
        RPN_POST_NMS_TOP_N=2000,
        RPN_BBOX_INSIDE_WEIGHTS=(1.0, 1.0, 1.0, 1.0),
        TRUNCATED=False,
        BBOX_NORMALIZE_MEANS=(0.0, 0.0, 0.0, 0.0),
        BBOX_NORMALIZE_STDS=(0.1, 0.1, 0.2, 0.2),
        BBOX_INSIDE_WEIGHTS=(1.0, 1.0, 1.0, 1.0),
        RPN_MIN_SIZE=8,
        RPN_CLOBBER_POSITIVES=False,
        RPN_POSITIVE_WEIGHT=-1.0,
        BBOX_NORMALIZE_TARGETS_PRECOMPUTED=True,

    ),

    TEST=dict(
        img_path="/data0/datasets/det_vertical_defect/2/original",
        # img_path="/data1/3-组图分割/online-4M-0724-seg/vertical",
        save_dir="/data/zhangcc/data/tmp/test_results/",
        gpus=(1, ),
        SCALES=(600,),
        MAX_SIZE=6400,
        TEST_SCALE=160,
        SCALE_MULTIPLE_OF=32,
        iou_thresh=0.5,
        nms_thresh=0.25,
        thresh=0.8,
        small_object_size=0,
        RPN_PRE_NMS_TOP_N=6000,
        RPN_POST_NMS_TOP_N=300,
        RPN_NMS_THRESH=0.7,
        RPN_MIN_SIZE=8,
        gama=False,
    ),
)