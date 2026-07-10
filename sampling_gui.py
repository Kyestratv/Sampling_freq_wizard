import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from sampling_math import (
    UNIT_SCALES,
    Band,
    choose_display_limit,
    format_entry_value,
    format_frequency,
    get_bandpass_sampling_intervals,
    parse_frequency,
)
from spectrum_plot import SpectrumPlotter, configure_matplotlib


SLIDER_MIN = 0
SLIDER_MAX = 200
SLIDER_DEFAULTS = {"fs": 80, "low": 10, "high": 18}


class SamplingDemoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        configure_matplotlib()
        self.title("采样频谱演示工具")
        self.geometry("1380x920")
        self.minsize(1160, 780)

        self.fs_var = tk.StringVar(value="8000")
        self.low_var = tk.StringVar(value="1000")
        self.high_var = tk.StringVar(value="1800")
        self.fmax_var = tk.StringVar(value="")
        self.unit_var = tk.StringVar(value="Hz")
        self.previous_unit = "Hz"

        self.slider_mode_var = tk.BooleanVar(value=False)
        self.auto_range_var = tk.BooleanVar(value=True)
        self.show_negative_var = tk.BooleanVar(value=True)
        self.render_overlap_var = tk.BooleanVar(value=True)

        self.fs_slider_var = tk.IntVar(value=SLIDER_DEFAULTS["fs"])
        self.low_slider_var = tk.IntVar(value=SLIDER_DEFAULTS["low"])
        self.high_slider_var = tk.IntVar(value=SLIDER_DEFAULTS["high"])
        self.last_slider_values = dict(SLIDER_DEFAULTS)
        self._updating_sliders = False

        self._build_ui()
        self.update_plots()

    def _build_ui(self) -> None:
        self._configure_style()
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        controls = ttk.Frame(self, padding=(16, 16, 12, 16))
        controls.grid(row=0, column=0, sticky="ns")

        title = ttk.Label(controls, text="参数设置", style="Title.TLabel")
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        slider_mode_check = ttk.Checkbutton(
            controls,
            text="滑动条输入模式",
            variable=self.slider_mode_var,
            command=self._toggle_slider_mode,
        )
        slider_mode_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(controls, text="频率单位").grid(row=2, column=0, sticky="w", pady=6)
        self.unit_box = ttk.Combobox(
            controls,
            textvariable=self.unit_var,
            values=list(UNIT_SCALES.keys()),
            state="readonly",
            width=16,
        )
        self.unit_box.grid(row=2, column=1, sticky="ew", pady=6)
        self.unit_box.bind("<<ComboboxSelected>>", self._on_unit_changed)

        self.fs_label, self.fs_entry, self.fs_slider_frame = self._add_frequency_input(
            controls, 3, "采样频率 fs", self.fs_var, self.fs_slider_var, "fs"
        )
        self.low_label, self.low_entry, self.low_slider_frame = self._add_frequency_input(
            controls, 4, "带通信号下限 fL", self.low_var, self.low_slider_var, "low"
        )
        self.high_label, self.high_entry, self.high_slider_frame = self._add_frequency_input(
            controls, 5, "带通信号上限 fH", self.high_var, self.high_slider_var, "high"
        )

        self.auto_check = ttk.Checkbutton(
            controls,
            text="自动选择显示范围",
            variable=self.auto_range_var,
            command=self._toggle_fmax_entry,
        )
        self.auto_check.grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 2))

        self.fmax_label, self.fmax_entry = self._add_entry(controls, 7, "最大显示频率", self.fmax_var)

        show_negative_check = ttk.Checkbutton(
            controls,
            text="显示负频率",
            variable=self.show_negative_var,
            command=self._realtime_update_if_slider_mode,
        )
        show_negative_check.grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 2))

        overlap_check = ttk.Checkbutton(
            controls,
            text="重叠部分渲染为红色",
            variable=self.render_overlap_var,
            command=self._realtime_update_if_slider_mode,
        )
        overlap_check.grid(row=9, column=0, columnspan=2, sticky="w", pady=(6, 2))

        self.update_button = ttk.Button(controls, text="计算并更新", command=self.update_plots)
        self.update_button.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(16, 14))

        formula = (
            "带通采样区间：\n"
            "第 m 次折叠可用条件\n"
            "2 fH / m <= fs <= 2 fL / (m - 1)\n"
            "m = 2, 3, ... floor(fH / B)\n"
            "其中 B = fH - fL。\n"
            "普通奈奎斯特区间：fs >= 2 fH。"
        )
        formula_label = ttk.Label(controls, text=formula, justify="left", wraplength=330)
        formula_label.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(4, 14))

        self.status_label = ttk.Label(controls, text="", justify="left", wraplength=330)
        self.status_label.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        interval_title = ttk.Label(controls, text="可用采样频率区间", style="Section.TLabel")
        interval_title.grid(row=13, column=0, columnspan=2, sticky="w", pady=(8, 6))

        interval_frame = ttk.Frame(controls)
        interval_frame.grid(row=14, column=0, columnspan=2, sticky="nsew")
        controls.rowconfigure(14, weight=1)
        interval_frame.columnconfigure(0, weight=1)
        interval_frame.rowconfigure(0, weight=1)

        self.interval_text = tk.Text(
            interval_frame,
            width=39,
            height=18,
            wrap="word",
            relief="solid",
            borderwidth=1,
            font=("Consolas", 13),
        )
        self.interval_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(interval_frame, orient="vertical", command=self.interval_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.interval_text.configure(yscrollcommand=scrollbar.set)
        self.interval_text.tag_configure("ok", foreground="#0b6b3a", font=("Consolas", 13, "bold"))
        self.interval_text.tag_configure("normal", foreground="#202020", font=("Consolas", 13))
        self.interval_text.tag_configure("muted", foreground="#666666", font=("Microsoft YaHei", 12))

        plot_frame = ttk.Frame(self, padding=(4, 12, 14, 12))
        plot_frame.grid(row=0, column=1, sticky="nsew")
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)

        self.figure, self.axes = plt.subplots(3, 1, figsize=(10.8, 8.4), constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        self._set_unit_labels()
        self._show_text_inputs()
        self._toggle_fmax_entry()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure(".", font=("Microsoft YaHei", 12))
        style.configure("Title.TLabel", font=("Microsoft YaHei", 16, "bold"))
        style.configure("Section.TLabel", font=("Microsoft YaHei", 13, "bold"))
        style.configure("TButton", font=("Microsoft YaHei", 12))
        style.configure("TCheckbutton", font=("Microsoft YaHei", 12))
        style.configure("TCombobox", font=("Microsoft YaHei", 12))

    def _add_entry(
        self,
        parent: ttk.Frame,
        row: int,
        label_text: str,
        variable: tk.StringVar,
    ) -> tuple[ttk.Label, ttk.Entry]:
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky="w", pady=6)
        entry = ttk.Entry(parent, textvariable=variable, width=18, font=("Microsoft YaHei", 12))
        entry.grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)
        return label, entry

    def _add_frequency_input(
        self,
        parent: ttk.Frame,
        row: int,
        label_text: str,
        entry_var: tk.StringVar,
        slider_var: tk.IntVar,
        key: str,
    ) -> tuple[ttk.Label, ttk.Entry, ttk.Frame]:
        label, entry = self._add_entry(parent, row, label_text, entry_var)
        slider_frame = ttk.Frame(parent)
        slider = tk.Scale(
            slider_frame,
            variable=slider_var,
            from_=SLIDER_MIN,
            to=SLIDER_MAX,
            orient="horizontal",
            resolution=1,
            showvalue=True,
            length=215,
            font=("Microsoft YaHei", 10),
            command=lambda _value, item=key: self._on_slider_changed(item),
        )
        slider.grid(row=0, column=0, sticky="ew")
        slider_frame.columnconfigure(0, weight=1)
        return label, entry, slider_frame

    def _set_unit_labels(self) -> None:
        unit = self.unit_var.get()
        self.fs_label.configure(text=f"采样频率 fs ({unit})")
        self.low_label.configure(text=f"带通信号下限 fL ({unit})")
        self.high_label.configure(text=f"带通信号上限 fH ({unit})")
        self.fmax_label.configure(text=f"最大显示频率 ({unit})")

    def _toggle_fmax_entry(self) -> None:
        state = "disabled" if self.auto_range_var.get() else "normal"
        self.fmax_label.configure(state=state)
        self.fmax_entry.configure(state=state)
        self._realtime_update_if_slider_mode()

    def _toggle_slider_mode(self) -> None:
        if self.slider_mode_var.get():
            self._enter_slider_mode()
        else:
            self._exit_slider_mode()

    def _enter_slider_mode(self) -> None:
        old_unit = self.unit_var.get()
        converted_fmax = None
        if self.fmax_var.get().strip():
            try:
                converted_fmax = parse_frequency(self.fmax_var.get(), "最大显示频率", old_unit)
            except ValueError:
                converted_fmax = None

        self._load_slider_values_from_entries()
        self.unit_var.set("Hz")
        self.previous_unit = "Hz"
        if converted_fmax is not None:
            self.fmax_var.set(format_entry_value(converted_fmax, "Hz"))
        self._set_unit_labels()
        self.unit_box.configure(state="disabled")
        self.update_button.configure(text="实时更新", state="disabled")
        self._show_slider_inputs()
        self.update_plots()

    def _exit_slider_mode(self) -> None:
        self.unit_box.configure(state="readonly")
        self.update_button.configure(text="计算并更新", state="normal")
        self._show_text_inputs()

    def _show_slider_inputs(self) -> None:
        for entry, slider_frame in (
            (self.fs_entry, self.fs_slider_frame),
            (self.low_entry, self.low_slider_frame),
            (self.high_entry, self.high_slider_frame),
        ):
            info = entry.grid_info()
            entry.grid_remove()
            slider_frame.grid(row=info["row"], column=info["column"], sticky="ew", pady=4)

    def _show_text_inputs(self) -> None:
        for entry, slider_frame in (
            (self.fs_entry, self.fs_slider_frame),
            (self.low_entry, self.low_slider_frame),
            (self.high_entry, self.high_slider_frame),
        ):
            slider_frame.grid_remove()
            entry.grid()

    def _load_slider_values_from_entries(self) -> None:
        try:
            fs = parse_frequency(self.fs_var.get(), "采样频率 fs", self.unit_var.get())
            low = parse_frequency(self.low_var.get(), "频率下限 fL", self.unit_var.get(), allow_zero=True)
            high = parse_frequency(self.high_var.get(), "频率上限 fH", self.unit_var.get())
            values = {"fs": round(fs), "low": round(low), "high": round(high)}
            if not self._slider_values_valid(values["fs"], values["low"], values["high"]):
                raise ValueError
        except ValueError:
            values = dict(SLIDER_DEFAULTS)

        self._set_slider_values(values)

    def _set_slider_values(self, values: dict[str, float]) -> None:
        self._updating_sliders = True
        self.fs_slider_var.set(values["fs"])
        self.low_slider_var.set(values["low"])
        self.high_slider_var.set(values["high"])
        self._updating_sliders = False
        self.last_slider_values = dict(values)
        self._sync_entry_vars_from_sliders()

    def _slider_values_valid(self, fs: float, low: float, high: float) -> bool:
        return (
            SLIDER_MIN < fs <= SLIDER_MAX
            and SLIDER_MIN <= low <= SLIDER_MAX
            and SLIDER_MIN < high <= SLIDER_MAX
            and low < high
        )

    def _on_slider_changed(self, key: str) -> None:
        if self._updating_sliders or not self.slider_mode_var.get():
            return

        values = {
            "fs": self.fs_slider_var.get(),
            "low": self.low_slider_var.get(),
            "high": self.high_slider_var.get(),
        }
        if not self._slider_values_valid(values["fs"], values["low"], values["high"]):
            self._restore_slider_value(key)
            return

        self.last_slider_values = dict(values)
        self._sync_entry_vars_from_sliders()
        self.update_plots()

    def _restore_slider_value(self, key: str) -> None:
        self._updating_sliders = True
        if key == "fs":
            self.fs_slider_var.set(self.last_slider_values["fs"])
        elif key == "low":
            self.low_slider_var.set(self.last_slider_values["low"])
        elif key == "high":
            self.high_slider_var.set(self.last_slider_values["high"])
        self._updating_sliders = False
        self._sync_entry_vars_from_sliders()

    def _sync_entry_vars_from_sliders(self) -> None:
        self.fs_var.set(format_entry_value(self.fs_slider_var.get(), "Hz"))
        self.low_var.set(format_entry_value(self.low_slider_var.get(), "Hz"))
        self.high_var.set(format_entry_value(self.high_slider_var.get(), "Hz"))

    def _realtime_update_if_slider_mode(self) -> None:
        if self.slider_mode_var.get():
            self.update_plots()

    def _on_unit_changed(self, _event: object | None = None) -> None:
        if self.slider_mode_var.get():
            self.unit_var.set("Hz")
            self.previous_unit = "Hz"
            return

        old_unit = self.previous_unit
        new_unit = self.unit_var.get()
        if old_unit == new_unit:
            return

        try:
            fs = parse_frequency(self.fs_var.get(), "采样频率 fs", old_unit)
            low = parse_frequency(self.low_var.get(), "频率下限 fL", old_unit, allow_zero=True)
            high = parse_frequency(self.high_var.get(), "频率上限 fH", old_unit)
            fmax = None
            if self.fmax_var.get().strip():
                fmax = parse_frequency(self.fmax_var.get(), "最大显示频率", old_unit)
        except ValueError:
            self.previous_unit = new_unit
            self._set_unit_labels()
            return

        self.fs_var.set(format_entry_value(fs, new_unit))
        self.low_var.set(format_entry_value(low, new_unit))
        self.high_var.set(format_entry_value(high, new_unit))
        if fmax is not None:
            self.fmax_var.set(format_entry_value(fmax, new_unit))

        self.previous_unit = new_unit
        self._set_unit_labels()

    def _read_inputs(self) -> tuple[float, Band, float]:
        unit = self.unit_var.get()
        if self.slider_mode_var.get():
            fs = self.fs_slider_var.get()
            low = self.low_slider_var.get()
            high = self.high_slider_var.get()
            unit = "Hz"
        else:
            fs = parse_frequency(self.fs_var.get(), "采样频率 fs", unit)
            low = parse_frequency(self.low_var.get(), "频率下限 fL", unit, allow_zero=True)
            high = parse_frequency(self.high_var.get(), "频率上限 fH", unit)

        band = Band(low=low, high=high)

        if self.auto_range_var.get() or not self.fmax_var.get().strip():
            fmax = choose_display_limit(fs, band)
        else:
            fmax = parse_frequency(self.fmax_var.get(), "最大显示频率", unit)
            if fmax < band.high:
                raise ValueError("最大显示频率必须不小于 fH")
        return fs, band, fmax

    def update_plots(self) -> None:
        unit = "Hz" if self.slider_mode_var.get() else self.unit_var.get()
        try:
            fs, band, fmax = self._read_inputs()
            intervals = get_bandpass_sampling_intervals(band)
        except ValueError as exc:
            self.status_label.configure(text=f"输入错误：{exc}", foreground="#b00020")
            return

        valid_now = any(interval.contains(fs) for interval in intervals)
        status = "当前 fs 位于可用区间内" if valid_now else "当前 fs 不在无混叠采样区间内"
        status_color = "#0b6b3a" if valid_now else "#b00020"
        self.status_label.configure(
            text=(
                f"{status}\n"
                f"信号带宽 B = {format_frequency(band.width, unit)}\n"
                f"普通奈奎斯特要求 fs >= {format_frequency(2 * band.high, unit)}"
            ),
            foreground=status_color,
        )

        self._update_interval_text(intervals, fs, unit)
        plotter = SpectrumPlotter(self.axes, unit, self.show_negative_var.get())
        plotter.draw_all(fs, band, fmax, self.render_overlap_var.get())
        self.canvas.draw_idle()

    def _update_interval_text(self, intervals, fs: float, unit: str) -> None:
        self.interval_text.configure(state="normal")
        self.interval_text.delete("1.0", "end")

        for interval in intervals:
            active = interval.contains(fs)
            tag = "ok" if active else "normal"
            prefix = "* " if active else "  "
            if interval.high is None:
                line = f"{prefix}m={interval.order:<2} fs >= {format_frequency(interval.low, unit)}\n"
            else:
                line = (
                    f"{prefix}m={interval.order:<2} "
                    f"{format_frequency(interval.low, unit)} <= fs <= {format_frequency(interval.high, unit)}\n"
                )
            self.interval_text.insert("end", line, tag)

        self.interval_text.insert("end", "\n* 表示当前输入的 fs 所在区间。\n", "muted")
        self.interval_text.configure(state="disabled")


if __name__ == "__main__":
    try:
        app = SamplingDemoApp()
        app.mainloop()
    except Exception as error:
        messagebox.showerror("程序错误", str(error))
