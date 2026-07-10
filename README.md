# 采样频谱演示工具

这是一个用 Python + Tkinter + Matplotlib 编写的小型图形化程序。

## 运行方式

```powershell
python .\sampling_gui.py
```

已经打包好的 Windows 可执行文件位于：

```text
dist\SamplingSpectrumDemo.exe
```

如果缺少绘图库，先安装：

```powershell
python -m pip install matplotlib numpy
```

## 重新打包

```powershell
.\build_exe.ps1
```

打包脚本会把 Tcl/Tk 运行库复制到本项目的 `runtime_tcl` 目录，再使用 PyInstaller 生成单文件 exe。

## 功能

- 输入采样频率 `fs`，显示采样冲击串在频域中的谱线，谱线间隔为 `fs`。
- 输入带通信号频率区间 `[fL, fH]`，用梯形显示正、负频带，方便观察频谱方向。
- 修改参数后点击“计算并更新”才会重新计算和刷新图表。
- 可开启滑动条输入模式；该模式下 `fs`、`fL`、`fH` 使用 0 到 200 Hz 的整数滑条输入，单位固定为 Hz，并实时计算和刷新图表。
- 显示采样后频谱复制结果，并用 `1st`、`2nd` 等标示奈奎斯特区。
- 可选择是否显示负频率。
- 可选择是否把原频谱与反转频谱的重叠区域按实际梯形交叠形状渲染为红色。
- 频率单位可选 `Hz`、`kHz`、`MHz`、`GHz`，输入、坐标轴和计算结果会使用同一单位。
- 自动计算无混叠采样频率区间，包括普通奈奎斯特采样和带通采样区间。

## 文件结构

- `sampling_gui.py`：界面、事件处理和参数读取。
- `sampling_math.py`：频率单位换算、输入解析、带通采样区间计算。
- `spectrum_plot.py`：Matplotlib 绘图，包括梯形频谱、奈奎斯特区和频谱复制。

## 带通采样公式

设信号频带为 `[fL, fH]`，带宽 `B = fH - fL`。

普通低通式采样要求：

```text
fs >= 2 fH
```

带通采样可用区间为：

```text
2 fH / m <= fs <= 2 fL / (m - 1)
m = 2, 3, ..., floor(fH / B)
```

程序会在右侧列表中用 `*` 标出当前输入的 `fs` 所在区间。
