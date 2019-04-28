from torch import nn
import torch
from torchviz import make_dot

"""
    Reference:
        [1] https://arxiv.org/pdf/1610.02357.pdf
        [2] Chollet, F.: Xception: Deep learning with depthwise separable convolutions. In: CVPR. (2017)
        [3] Qi, H., Zhang, Z., Xiao, B., Hu, H., Cheng, B., Wei, Y., Dai, J.: Deformable convolutional networks – coco detection and segmentation challenge 2017 entry. ICCV COCO Challenge Workshop (2017)
        [4] https://github.com/tstandley/Xception-PyTorch
"""

class SeparableConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=1, stride=1, padding=0, dilation=1, bias=False,
                 depth_activation=True):
        super(SeparableConv2d, self).__init__()
        self.relu_0 = nn.ReLU(True)

        self.depthwise = nn.Conv2d(in_channels, in_channels, kernel_size=kernel_size, stride=stride, padding=padding,
                                   dilation=dilation, bias=bias, groups=in_channels)
        self.bn_1 = nn.BatchNorm2d(in_channels)
        self.relu_1 = nn.ReLU(True)

        self.pointwise = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=bias)
        self.bn_2 = nn.BatchNorm2d(out_channels)
        self.relu_2 = nn.ReLU(True)

        self.depth_activation = depth_activation

    def forward(self, x):
        if not self.depth_activation:
            x = self.relu_0(x)
        x = self.depthwise(x)
        x = self.bn_1(x)
        if self.depth_activation:
            x = self.relu_1(x)
        x = self.pointwise(x)
        x = self.bn_2(x)
        if self.depth_activation:
            x = self.relu_2(x)
        return x

class Block(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dilation=1, bias=False,
                 depth_activation=True, grow_first=True):
        super(Block, self).__init__()

        if in_channels != out_channels or stride != 1:
            self.skip = nn.Conv2d(in_channels, out_channels, 1, stride=stride, bias=False)
            self.skip_bn = nn.BatchNorm2d(out_channels)
        else:
            self.skip = None

        if grow_first:
            inner_channels = out_channels
        else:
            inner_channels = in_channels

        self.layer_1 = SeparableConv2d(in_channels, inner_channels, 3, stride=1, padding=dilation, dilation=dilation,
                                       bias=False, depth_activation=depth_activation)
        self.layer_2 = SeparableConv2d(inner_channels, out_channels, 3, stride=1, padding=dilation, dilation=dilation,
                                       bias=False, depth_activation=depth_activation)
        self.layer_3 = SeparableConv2d(out_channels,out_channels,3,stride=stride, padding=dilation,dilation=dilation,
                                        bias=False,depth_activation=depth_activation)

    def forward(self, x):
        skip = x
        if self.skip != None:
            skip = self.skip(x)
            skip = self.skip_bn(skip)
        main = self.layer_1(x)
        main = self.layer_2(main)
        main = self.layer_3(main)

        main += skip
        return main

class Xception(nn.Module):
    def __init__(self, nbr_classes=1000, os=8):
        super(Xception, self).__init__()

        strides = None
        if os == 8:
            strides = [2,1,1]
        elif os == 16:
            strides = [2,2,1]

        self.conv_1 = nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn_1 = nn.BatchNorm2d(32)
        self.relu = nn.ReLU(True)
        self.conv_2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn_2 = nn.BatchNorm2d(64)

        self.block_1 = Block(64, 128, stride=2)
        self.block_2 = Block(128, 256, stride=strides[0])
        self.block_3 = Block(256, 728, stride=strides[1])

        rate = 16 // os
        self.blocks = nn.ModuleList([Block(728, 728, 1, dilation=rate) for _ in range(16)])
        self.block_20 = Block(728, 1024, strides[2], dilation=rate, grow_first=False)

        self.conv_3 = SeparableConv2d(1024, 1536, kernel_size=3, stride=1,padding=rate,
                                      dilation=rate,depth_activation=True)

        self.conv_4 = SeparableConv2d(1536, 1536, kernel_size=3, stride=1, padding=rate,
                                      dilation=rate, depth_activation=True)

        self.conv_5 = SeparableConv2d(1536, 2048, kernel_size=3, stride=1, padding=rate,
                                      dilation=rate, depth_activation=True)

        for layer in self.modules():
            if isinstance(layer, nn.Conv2d):
                nn.init.xavier_uniform_(layer.weight)
            elif isinstance(layer, nn.BatchNorm2d):
                layer.weight.data.fill_(1)
                layer.bias.data.zero_()

    def forward(self, x):
        x = self.conv_1(x)
        x = self.bn_1(x)
        x = self.relu(x)

        x = self.conv_2(x)
        x = self.bn_2(x)
        x = self.relu(x)

        x = self.block_1(x)
        x = self.block_2(x)
        x = self.block_3(x)

        for block in self.blocks:
            x = block(x)

        x = self.block_20(x)
        x = self.conv_3(x)
        x = self.conv_4(x)
        x = self.conv_5(x)

        return x


def get_xception():
    def build_net(backbone_pretrained_path='./weights/xception.pth', nbr_classes=1000,
                  backbone_pretrained=True, os=16, **kwargs):
        model = Xception(nbr_classes, os=os)
        if backbone_pretrained:
            model.load_state_dict(torch.load(backbone_pretrained_path), strict=True)
            print('xception weights are loaded successfully')
        return model

    return build_net

if __name__ == '__main__':
    model = get_xception()(backbone_pretrained_path='../weights/xception.pth')
    # g = make_dot(model(torch.rand(16, 3, 384, 384)), params=dict(model.named_parameters()))
    # g.render('xception')

    params = list(model.parameters())
    k = 0
    for i in params:
        l = 1
        print("layer architecture：" + str(list(i.size())))
        for j in i.size():
            l *= j
        print("the number of parameters：" + str(l))
        k = k + l
    print("the total of parameters：" + str(k))
