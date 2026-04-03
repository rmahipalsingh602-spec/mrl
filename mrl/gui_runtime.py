from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class UIElementSpec:
    kind: str
    text: str


@dataclass(frozen=True, slots=True)
class UIWindowSpec:
    title: str
    elements: list[UIElementSpec]


class GUIRuntime:
    def __init__(self, *, headless: bool | None = None) -> None:
        if headless is None:
            headless = os.environ.get("MRL_HEADLESS", "0") == "1"
        self.headless = headless

    def definition_from_model(self, model: dict[str, Any]) -> UIWindowSpec:
        elements = [UIElementSpec(kind=item["kind"], text=item["text"]) for item in model.get("elements", [])]
        return UIWindowSpec(title=str(model.get("title", "MRL App")), elements=elements)

    def preview(self, definition: UIWindowSpec) -> str:
        rendered = ", ".join(f"{element.kind}('{element.text}')" for element in definition.elements)
        return f"[ui] {definition.title}: {rendered}" if rendered else f"[ui] {definition.title}: <empty>"

    def render_definition(self, definition: UIWindowSpec, *, run_mainloop: bool = True) -> str:
        preview = self.preview(definition)
        if self.headless:
            return preview

        try:
            import tkinter as tk
        except Exception as exc:  # pragma: no cover - environment dependent
            return f"{preview} [GUI fallback: {exc}]"

        try:
            root = tk.Tk()
            root.title(definition.title)
            root.configure(bg="#0e1220")
            root.geometry("560x360")

            frame = tk.Frame(root, bg="#0e1220", padx=24, pady=24)
            frame.pack(fill="both", expand=True)

            header = tk.Label(
                frame,
                text=definition.title,
                font=("Segoe UI", 22, "bold"),
                fg="#f7fbff",
                bg="#0e1220",
            )
            header.pack(anchor="w", pady=(0, 18))

            for element in definition.elements:
                if element.kind == "text":
                    widget = tk.Label(
                        frame,
                        text=element.text,
                        font=("Segoe UI", 13),
                        fg="#d9e7ff",
                        bg="#0e1220",
                        anchor="w",
                        justify="left",
                    )
                    widget.pack(fill="x", pady=6)
                elif element.kind == "button":
                    widget = tk.Button(
                        frame,
                        text=element.text,
                        font=("Segoe UI", 12, "bold"),
                        bg="#32d1ff",
                        fg="#07111f",
                        activebackground="#7ce6ff",
                        relief="flat",
                        padx=14,
                        pady=8,
                    )
                    widget.pack(anchor="w", pady=8)

            if run_mainloop:
                root.mainloop()
            else:
                root.update_idletasks()
                root.destroy()
        except Exception as exc:  # pragma: no cover - environment dependent
            return f"{preview} [GUI fallback: {exc}]"

        return preview