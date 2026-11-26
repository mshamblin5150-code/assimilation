// One requested action on the element at a path, as REA 6.8.0's Swift helper does it: walk the
// path again (it can change as the UI changes), check the element's owner, then press, step or
// set the value. An element that cannot do it fails; nothing is simulated instead.
namespace ReaWindowsUi;

/// <summary>A scenario step's action: kind click, scroll (direction) or key-entry (text).</summary>
public sealed record UiAction(string Kind, int[]? Path, string? Direction, string? Text);

/// <summary>A failure with one of REA's stable codes (target-mismatch, element-missing...).</summary>
public sealed class HelperFailure(string code, string message) : Exception(message)
{
    public string Code { get; } = code;
}

public static class UiActions
{
    public static void Perform(IUiElement root, UiAction action, int expectedProcessId)
    {
        var element = Resolve(root, action.Path ?? []);
        int owner;
        try { owner = element.ProcessId; }
        catch (Exception) { owner = -1; } // as Swift: an unreadable owner is a mismatch
        if (owner != expectedProcessId)
            throw new HelperFailure("element-owner-mismatch", "Selected element belongs to another process");
        try
        {
            switch (action.Kind)
            {
                case "click": element.Invoke(); break;
                case "scroll": element.Step(action.Direction == "increment"); break;
                case "key-entry": element.SetValue(action.Text ?? ""); break;
                default:
                    throw new HelperFailure(
                        "unsupported-action", "Only selected-element press, increment/decrement and text-value entry are admitted");
            }
        }
        catch (HelperFailure)
        {
            throw;
        }
        catch (Exception failed) // not enabled, gone, invalid value: Swift maps every AXError alike
        {
            throw new HelperFailure("action-failed", $"UI Automation action failed: {failed.Message}");
        }
    }

    private static IUiElement Resolve(IUiElement root, int[] path)
    {
        var element = root;
        foreach (var index in path)
        {
            var count = element.ChildCount()
                ?? throw new HelperFailure(
                    "element-count-unavailable",
                    "Cannot validate selected accessibility path because the UI Automation child count is unavailable");
            if (index < 0 || index >= count)
                throw new HelperFailure("element-missing", "Selected accessibility path no longer exists");
            var children = element.Children(index + 1);
            if (children.Count <= index)
                throw new HelperFailure("element-missing", "Selected accessibility path no longer exists");
            element = children[index];
        }
        return element;
    }
}
