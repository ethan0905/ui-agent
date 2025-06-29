# macos_agent_ui.py
#
# Single‑line ChatGPT input bar — draggable pill — ⌘⇧C global toggle (AppKit).
# -----------------------------------------------------------------------------------
# Fixes in this revision (r8):
#   • **Shortcut finally works**: Replaced fragile Carbon code with robust
#     AppKit/NSEvent global + local monitors. macOS will prompt for
#     *Input‑Monitoring* permission on first use; grant it.
#   • Dragging still supported via setMovableByWindowBackground_ + background view.
# -----------------------------------------------------------------------------------

from Cocoa import (
    NSApplication,
    NSApp,
    NSObject,
    NSWindow,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskFullSizeContentView,
    NSBackingStoreBuffered,
    NSMakeRect,
    NSColor,
    NSVisualEffectMaterialSidebar,
    NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectStateActive,
    NSFont,
    NSTextField,
    NSButton,
    NSViewWidthSizable,
    NSVisualEffectView,
    NSEvent,
    NSEventMaskKeyDown,
    NSEventModifierFlagCommand,
    NSEventModifierFlagShift,
)
from PyObjCTools import AppHelper
import objc

# ---------------------------------------------------------------------------
# Helper: Draggable, vibrant background view
# ---------------------------------------------------------------------------
class DraggableVibrantView(NSVisualEffectView):
    def mouseDown_(self, event):
        self.window().performWindowDragWithEvent_(event)


# ---------------------------------------------------------------------------
# ChatAgentWindow
# ---------------------------------------------------------------------------
class ChatAgentWindow(NSWindow):
    BAR_HEIGHT = 60
    ARROW_SIZE = 28
    MARGIN = 14

    def init(self):
        frame = NSMakeRect(0, 0, 520, self.BAR_HEIGHT)
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskFullSizeContentView
        self = objc.super(ChatAgentWindow, self).initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        if self is None:
            return None

        # Window basics ---------------------------------------------------------
        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self.setMovableByWindowBackground_(True)
        # Rounded pill corners
        self.contentView().setWantsLayer_(True)
        self.contentView().layer().setCornerRadius_(self.BAR_HEIGHT / 2)
        self.contentView().layer().setMasksToBounds_(True)

        # Vibrant blur background ----------------------------------------------
        vibrant = DraggableVibrantView.alloc().initWithFrame_(self.contentView().bounds())
        vibrant.setAutoresizingMask_(NSViewWidthSizable)
        vibrant.setMaterial_(NSVisualEffectMaterialSidebar)
        vibrant.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        vibrant.setState_(NSVisualEffectStateActive)
        self.contentView().addSubview_(vibrant)

        # Font + baseline -------------------------------------------------------
        font = NSFont.systemFontOfSize_(14)
        line_height = font.defaultLineHeightForFont() + 2
        input_y = (self.BAR_HEIGHT - line_height) / 2

        # Text field ------------------------------------------------------------
        input_rect = NSMakeRect(
            self.MARGIN,
            input_y,
            frame.size.width - self.ARROW_SIZE - 3 * self.MARGIN,
            line_height,
        )
        input_field = NSTextField.alloc().initWithFrame_(input_rect)
        input_field.setPlaceholderString_("Message ChatGPT …")
        input_field.setUsesSingleLineMode_(True)
        input_field.setBezeled_(False)
        input_field.setBordered_(False)
        input_field.setDrawsBackground_(False)
        input_field.setFont_(font)
        vibrant.addSubview_(input_field)

        # Arrow button ----------------------------------------------------------
        arrow_x = frame.size.width - self.ARROW_SIZE - 1.5 * self.MARGIN
        arrow_y = (self.BAR_HEIGHT - self.ARROW_SIZE) / 2
        send_rect = NSMakeRect(arrow_x, arrow_y, self.ARROW_SIZE, self.ARROW_SIZE)
        send_btn = NSButton.alloc().initWithFrame_(send_rect)
        send_btn.setTitle_("➤")
        send_btn.setBordered_(False)
        send_btn.setFont_(NSFont.boldSystemFontOfSize_(18))
        send_btn.setContentTintColor_(NSColor.controlAccentColor())
        vibrant.addSubview_(send_btn)

        # Events ----------------------------------------------------------------
        input_field.setTarget_(self)
        input_field.setAction_("submit:")
        send_btn.setTarget_(self)
        send_btn.setAction_("submit:")

        self.input_field = input_field
        return self

    def submit_(self, _):
        txt = self.input_field.stringValue().strip()
        if not txt:
            return
        print("You:", txt)
        self.input_field.setStringValue_("")
        # TODO: hook up LLM call here


# ---------------------------------------------------------------------------
# AppDelegate with ⌘⇧C shortcut via NSEvent monitors
# ---------------------------------------------------------------------------
class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, _):
        # Window ---------------------------------------------------------------
        self.window = ChatAgentWindow.alloc().init()
        self.window.center()
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

        # Shortcut -------------------------------------------------------------
        self._install_shortcut()

    # Install both local (while app front‑most) and global (background) monitors
    def _install_shortcut(self):
        flags_required = NSEventModifierFlagCommand | NSEventModifierFlagShift

        def handler(event):
            if (
                event.type() == 10  # NSEventTypeKeyDown (PyObjC constant missing)
                and event.charactersIgnoringModifiers().lower() == "c"
                and (event.modifierFlags() & flags_required) == flags_required
            ):
                self.toggleWindow()
            return event  # for local monitor only

        # Global: no return value needed
        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSEventMaskKeyDown, handler)
        # Local: must return event so others receive it
        NSEvent.addLocalMonitorForEventsMatchingMask_handler_(NSEventMaskKeyDown, handler)

    # Show / hide --------------------------------------------------------------
    def toggleWindow(self):
        if self.window.isVisible():
            self.window.orderOut_(None)
        else:
            self.window.center()
            self.window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)


if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()

