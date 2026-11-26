// The accessibility side of one capture, kept apart from Windows so it can be tested on a fake
// tree. The walk is REA 6.8.0's (bridge/native/ReaNativeUI.swift): depth-first via a pending
// stack, paths of child indices, a node budget that counts children already queued, depth 32,
// and every unread part reported as truncated plus a gap.
namespace ReaWindowsUi;

/// <summary>What the walk and the actions need from one accessibility element.</summary>
public interface IUiElement
{
    string? Role { get; }
    string? Title { get; }
    /// <summary>A string, double or bool, or null when the element exposes no value.</summary>
    object? Value { get; }
    IReadOnlyList<string> Actions { get; }
    int ProcessId { get; }
    /// <summary>The number of children, or null when it cannot be read.</summary>
    int? ChildCount();
    IReadOnlyList<IUiElement> Children(int count);
    void Invoke();
    void Step(bool increment);
    void SetValue(string text);
}

/// <summary>The element cannot do the requested action (no fallback is attempted).</summary>
public sealed class UnsupportedActionException(string action) : Exception($"Element does not support {action}");

public sealed record UiNode(
    int[] Path, string? Role, string? Title, object? Value, IReadOnlyList<string> Actions, int? ChildrenCount);

public sealed record UiCapture(IReadOnlyList<UiNode> Nodes, bool Truncated, IReadOnlyList<string> Gaps);

public static class UiTree
{
    public const int MaxDepth = 32;

    public static UiCapture Capture(IUiElement root, int maxNodes)
    {
        var nodes = new List<UiNode>();
        var gaps = new List<string>();
        var truncated = false;
        var pending = new Stack<(IUiElement Element, int[] Path)>();
        pending.Push((root, []));
        while (pending.Count > 0)
        {
            var (element, path) = pending.Pop();
            if (nodes.Count >= maxNodes) { truncated = true; break; }
            var total = element.ChildCount();
            var value = element.Value;
            if (value is double number && !double.IsFinite(number))
            {
                // As Swift's captureAccessibilityValue: an unrepresentable value is a gap.
                gaps.Add($"UI Automation value is not a finite number at path [{string.Join(", ", path)}]");
                truncated = true;
                value = null;
            }
            nodes.Add(new UiNode(path, element.Role, element.Title, value, element.Actions, total));
            if (total is null)
            {
                truncated = true;
                gaps.Add($"UI Automation child count unavailable at path [{string.Join(", ", path)}]");
                continue;
            }
            if (path.Length >= MaxDepth) { if (total > 0) truncated = true; continue; }
            var available = Math.Max(0, maxNodes - nodes.Count - pending.Count);
            var count = Math.Min(available, total.Value);
            var children = element.Children(count);
            if (children.Count < count || total > count) truncated = true;
            for (var index = children.Count - 1; index >= 0; index--)
                pending.Push((children[index], [.. path, index]));
        }
        return new UiCapture(nodes, truncated, gaps);
    }
}
