// The Windows counterpart of REA 6.8.0's bridge/native/ReaNativeUI.swift: one JSON request in
// (argument 1), one JSON line out: {"ok":true,"result":snapshot} or {"ok":false,"code","message"}.
// Checks the running process against the active target, the window against the process, then
// performs the one optional action, walks the accessibility tree and captures the window.
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Interop;
using System.Windows.Media.Imaging;

namespace ReaWindowsUi;

public static class Program
{
    private const long IdentityBudgetBytes = 256L * 1024 * 1024;

    [STAThread]
    public static int Main(string[] args)
    {
        Native.SetProcessDpiAwarenessContext(-4); // per-monitor v2: physical pixels
        JsonNode response;
        try
        {
            // The request arrives on stdin (a Windows command line is capped near 32K characters).
            var text = args.Length > 0 ? args[0] : Console.In.ReadToEnd();
            var request = JsonNode.Parse(text)!.AsObject();
            response = new JsonObject { ["ok"] = true, ["result"] = Observe(request) };
        }
        catch (HelperFailure failure)
        {
            response = new JsonObject { ["ok"] = false, ["code"] = failure.Code, ["message"] = failure.Message };
        }
        catch (Exception error)
        {
            response = new JsonObject { ["ok"] = false, ["code"] = "capture-failed", ["message"] = error.Message };
        }
        Console.OutputEncoding = new UTF8Encoding(false);
        Console.Out.Write(response.ToJsonString());
        return 0;
    }

    private static JsonObject Observe(JsonObject request)
    {
        var pid = request["pid"]!.GetValue<int>();
        var windowId = request["window_id"]!.GetValue<long>();
        var executable = request["executable"]!.GetValue<string>();
        var sha256 = request["sha256"]!.GetValue<string>();
        var screenshot = request["screenshot"]?.GetValue<bool>() ?? true;
        var accessibility = request["accessibility"]?.GetValue<bool>() ?? true;
        var maxNodes = request["max_nodes"]?.GetValue<int>() ?? 500;

        // Limited query rights only, so an elevated target reports the right refusal.
        var handle = Native.OpenProcess(0x1000, false, (uint)pid); // PROCESS_QUERY_LIMITED_INFORMATION
        if (handle == IntPtr.Zero)
        {
            if (Marshal.GetLastWin32Error() == 5) // ERROR_ACCESS_DENIED
                throw new HelperFailure("application-executable-unavailable",
                    "The selected process refuses identity queries (it runs at a higher integrity level); run the observer at the same level, then retry");
            throw new HelperFailure("pid-not-application",
                "Windows does not expose a running process for the selected PID; this does not establish that the process is absent");
        }
        string running;
        double launch;
        try
        {
            var image = Native.ImagePath(handle)
                ?? throw new HelperFailure("application-executable-unavailable",
                    "The selected process does not expose an executable path; select a PID with an identifiable executable");
            running = Native.FinalPath(image);
            launch = Native.StartTime(handle)
                ?? throw new HelperFailure("process-identity-unavailable",
                    "Selected process does not expose a start time; stable PID reuse checks are unavailable");
        }
        finally { Native.CloseHandle(handle); }
        if (!string.Equals(running, Native.FinalPath(executable), StringComparison.OrdinalIgnoreCase))
            throw new HelperFailure("target-mismatch", $"Selected PID executable {running} differs from active target {executable}");
        if (request["launch_time"] is JsonNode expected && expected.GetValue<double>() != launch)
            throw new HelperFailure("process-replaced", "Selected process was replaced");
        var size = new FileInfo(running).Length;
        if (size > IdentityBudgetBytes)
            throw new HelperFailure("target-limit", "Running executable exceeds the 256 MiB identity-check budget");
        using (var stream = File.OpenRead(running))
            if (!string.Equals(Convert.ToHexStringLower(SHA256.HashData(stream)), sha256, StringComparison.Ordinal))
                throw new HelperFailure("target-mismatch", "Running executable bytes differ from the active target digest");

        var hwnd = new IntPtr(windowId);
        if (!Native.IsWindow(hwnd) || Native.OwnerPid(hwnd) != pid || Native.GetAncestor(hwnd, 2) != hwnd || !Native.IsWindowVisible(hwnd))
            throw new HelperFailure("window-mismatch", "Selected window is absent, not a visible top-level window, or belongs to another process");

        IUiElement? root = null;
        if (accessibility || request["action"] is not null)
        {
            try { root = new UiaElement(AutomationElement.FromHandle(hwnd)); }
            catch (UnauthorizedAccessException)
            {
                throw new HelperFailure("accessibility-denied",
                    "UI Automation was refused (the target runs at a higher integrity level); run the observer at the same level, then retry");
            }
            catch (Exception error)
            {
                throw new HelperFailure("accessibility-unavailable", $"Selected window does not expose UI Automation: {error.Message}");
            }
        }
        if (request["action"] is JsonObject action && root is not null)
            UiActions.Perform(root, new UiAction(
                action["kind"]!.GetValue<string>(),
                action["path"]?.AsArray().Select(n => n!.GetValue<int>()).ToArray(),
                action["direction"]?.GetValue<string>(),
                action["text"]?.GetValue<string>()), pid);

        var nodes = new JsonArray();
        var truncated = false;
        var gaps = new JsonArray();
        if (accessibility && root is not null)
        {
            var capture = UiTree.Capture(root, maxNodes);
            foreach (var node in capture.Nodes) nodes.Add(NodeJson(node));
            truncated = capture.Truncated;
            foreach (var gap in capture.Gaps) gaps.Add(gap);
        }
        else gaps.Add("Accessibility capture was disabled");

        return new JsonObject
        {
            ["window"] = new JsonObject
            {
                ["pid"] = pid, ["window_id"] = windowId, ["executable"] = executable,
                ["launch_time"] = launch, ["title"] = Native.Title(hwnd),
            },
            ["nodes"] = nodes,
            ["truncated"] = truncated,
            ["screenshot"] = screenshot ? Screenshot(hwnd) : null,
            ["gaps"] = gaps,
        };
    }

    private static JsonObject NodeJson(UiNode node) => new()
    {
        ["path"] = new JsonArray(node.Path.Select(i => (JsonNode)i).ToArray()),
        ["role"] = node.Role,
        ["title"] = node.Title,
        ["value"] = node.Value switch
        {
            string text => text,
            double number when double.IsFinite(number) => number,
            bool flag => flag,
            _ => null,
        },
        ["actions"] = new JsonArray(node.Actions.Select(a => (JsonNode)a).ToArray()),
        ["children_count"] = node.ChildrenCount,
    };

    /// <summary>The window's own rendering, longer side at most 2048 px, as PNG.</summary>
    private static JsonObject Screenshot(IntPtr hwnd)
    {
        if (!Native.GetWindowRect(hwnd, out var rect))
            throw new HelperFailure("capture-window-missing", "Selected window disappeared before capture");
        int width = rect.Right - rect.Left, height = rect.Bottom - rect.Top;
        if (width <= 0 || height <= 0 || width > 100000 || height > 100000)
            throw new HelperFailure("window-bounds", "Selected window has invalid or oversized geometry");
        var screen = Native.GetDC(IntPtr.Zero);
        var memory = Native.CreateCompatibleDC(screen);
        var bitmap = Native.CreateCompatibleBitmap(screen, width, height);
        var previous = Native.SelectObject(memory, bitmap);
        try
        {
            if (!Native.PrintWindow(hwnd, memory, 2)) // PW_RENDERFULLCONTENT
                throw new HelperFailure("capture-failed", "Selected-window capture failed");
            Native.SelectObject(memory, previous);
            previous = IntPtr.Zero;
            BitmapSource image = Imaging.CreateBitmapSourceFromHBitmap(bitmap, IntPtr.Zero, Int32Rect.Empty, BitmapSizeOptions.FromEmptyOptions());
            // The visible frame only: GetWindowRect includes the invisible resize border.
            if (Native.FrameBounds(hwnd) is { } frame)
            {
                var crop = new Int32Rect(
                    Math.Max(0, frame.Left - rect.Left), Math.Max(0, frame.Top - rect.Top),
                    Math.Min(width, frame.Right - frame.Left), Math.Min(height, frame.Bottom - frame.Top));
                if (crop.Width > 0 && crop.Height > 0 && crop.X + crop.Width <= width && crop.Y + crop.Height <= height)
                    image = new CroppedBitmap(image, crop);
            }
            var longer = Math.Max(image.PixelWidth, image.PixelHeight);
            if (longer > 2048)
            {
                // As Swift: longer side at most 2048, each side at least 1 pixel.
                var scaleX = Math.Max(1.0, Math.Round(image.PixelWidth * 2048.0 / longer)) / image.PixelWidth;
                var scaleY = Math.Max(1.0, Math.Round(image.PixelHeight * 2048.0 / longer)) / image.PixelHeight;
                image = new TransformedBitmap(image, new System.Windows.Media.ScaleTransform(scaleX, scaleY));
            }
            var encoder = new PngBitmapEncoder();
            encoder.Frames.Add(BitmapFrame.Create(image));
            using var png = new MemoryStream();
            encoder.Save(png);
            var bytes = png.ToArray();
            return new JsonObject
            {
                ["mime_type"] = "image/png",
                ["base64"] = Convert.ToBase64String(bytes),
                ["sha256"] = Convert.ToHexStringLower(SHA256.HashData(bytes)),
                ["width"] = image.PixelWidth,
                ["height"] = image.PixelHeight,
            };
        }
        finally
        {
            if (previous != IntPtr.Zero) Native.SelectObject(memory, previous); // never delete a selected bitmap
            Native.DeleteObject(bitmap);
            Native.DeleteDC(memory);
            Native.ReleaseDC(IntPtr.Zero, screen);
        }
    }
}

internal static partial class Native
{
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left, Top, Right, Bottom; }

    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(nint value);
    [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr hwnd, uint flags);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out Rect rect);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowTextW(IntPtr hwnd, StringBuilder text, int max);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr dc, uint flags);
    [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr hwnd, IntPtr dc);
    [DllImport("gdi32.dll")] public static extern IntPtr CreateCompatibleDC(IntPtr dc);
    [DllImport("gdi32.dll")] public static extern IntPtr CreateCompatibleBitmap(IntPtr dc, int width, int height);
    [DllImport("gdi32.dll")] public static extern IntPtr SelectObject(IntPtr dc, IntPtr obj);
    [DllImport("gdi32.dll")] public static extern bool DeleteObject(IntPtr obj);
    [DllImport("gdi32.dll")] public static extern bool DeleteDC(IntPtr dc);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] private static extern bool QueryFullProcessImageNameW(IntPtr process, uint flags, StringBuilder name, ref uint size);

    [DllImport("kernel32.dll", SetLastError = true)] public static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
    [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] private static extern bool GetProcessTimes(IntPtr process, out long creation, out long exit, out long kernel, out long user);
    [DllImport("dwmapi.dll")] private static extern int DwmGetWindowAttribute(IntPtr hwnd, int attribute, out Rect value, int size);

    public static uint OwnerPid(IntPtr hwnd) { GetWindowThreadProcessId(hwnd, out var pid); return pid; }

    /// <summary>Process creation time in seconds since 1970, to the millisecond (stable across calls).</summary>
    public static double? StartTime(IntPtr process) =>
        GetProcessTimes(process, out var creation, out _, out _, out _)
            ? Math.Round((DateTime.FromFileTimeUtc(creation) - DateTime.UnixEpoch).TotalSeconds, 3)
            : null;

    /// <summary>The visible window frame (DWMWA_EXTENDED_FRAME_BOUNDS), or null.</summary>
    public static Rect? FrameBounds(IntPtr hwnd) =>
        DwmGetWindowAttribute(hwnd, 9, out var frame, Marshal.SizeOf<Rect>()) == 0 ? frame : null;

    /// <summary>The path with junctions and links resolved (cf. realpath), or the path as given.</summary>
    public static string FinalPath(string path)
    {
        try
        {
            var resolved = new FileInfo(path).ResolveLinkTarget(returnFinalTarget: true)?.FullName;
            var full = resolved ?? System.IO.Path.GetFullPath(path);
            // Directory junctions on the way (e.g. a junctioned install folder) resolve via the parent.
            var directory = new DirectoryInfo(System.IO.Path.GetDirectoryName(full)!);
            var parent = directory.ResolveLinkTarget(returnFinalTarget: true)?.FullName ?? directory.FullName;
            return System.IO.Path.Combine(parent, System.IO.Path.GetFileName(full));
        }
        catch (Exception) { return System.IO.Path.GetFullPath(path); }
    }

    public static string Title(IntPtr hwnd)
    {
        var text = new StringBuilder(512);
        GetWindowTextW(hwnd, text, text.Capacity);
        return text.ToString();
    }

    public static string? ImagePath(IntPtr process)
    {
        var name = new StringBuilder(1024);
        var size = (uint)name.Capacity;
        return QueryFullProcessImageNameW(process, 0, name, ref size) ? name.ToString() : null;
    }
}
