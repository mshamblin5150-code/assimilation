// IUiElement over Microsoft UI Automation (System.Windows.Automation), control view. Roles and
// actions use UI Automation's own vocabulary (control types and patterns), never macOS AX names.
using System.Windows.Automation;

namespace ReaWindowsUi;

public sealed class UiaElement(AutomationElement element) : IUiElement
{
    private static readonly TreeWalker Walker = TreeWalker.ControlViewWalker;

    public string? Role => Try(() => element.Current.ControlType.ProgrammaticName.Replace("ControlType.", ""));
    public string? Title => Try(() => element.Current.Name); // "" stays "", as Swift keeps an empty AXTitle
    public int ProcessId => element.Current.ProcessId;

    public object? Value => Try<object?>(() =>
    {
        if (element.TryGetCurrentPattern(RangeValuePattern.Pattern, out var range))
            return ((RangeValuePattern)range).Current.Value;
        if (element.TryGetCurrentPattern(TogglePattern.Pattern, out var toggle))
            return ((TogglePattern)toggle).Current.ToggleState switch
            {
                ToggleState.On => true,
                ToggleState.Off => false,
                _ => null,
            };
        if (element.TryGetCurrentPattern(ValuePattern.Pattern, out var value))
            return ((ValuePattern)value).Current.Value;
        return null;
    });

    public IReadOnlyList<string> Actions => Try(() =>
    {
        var actions = new List<string>();
        if (Has(InvokePattern.Pattern)) actions.Add("Invoke");
        if (element.TryGetCurrentPattern(RangeValuePattern.Pattern, out var range) && !((RangeValuePattern)range).Current.IsReadOnly)
            actions.AddRange(["Increment", "Decrement"]);
        if (element.TryGetCurrentPattern(ValuePattern.Pattern, out var value) && !((ValuePattern)value).Current.IsReadOnly)
            actions.Add("SetValue");
        if (Has(TogglePattern.Pattern)) actions.Add("Toggle");
        if (Has(ExpandCollapsePattern.Pattern)) actions.Add("ExpandCollapse");
        if (Has(SelectionItemPattern.Pattern)) actions.Add("Select");
        if (Has(ScrollPattern.Pattern)) actions.Add("Scroll");
        return (IReadOnlyList<string>)actions;
    }) ?? [];

    public int? ChildCount()
    {
        try
        {
            var count = 0;
            for (var child = Walker.GetFirstChild(element); child is not null; child = Walker.GetNextSibling(child))
                count++;
            return count;
        }
        catch (Exception) { return null; }
    }

    public IReadOnlyList<IUiElement> Children(int count)
    {
        var children = new List<IUiElement>();
        try
        {
            for (var child = Walker.GetFirstChild(element); child is not null && children.Count < count; child = Walker.GetNextSibling(child))
                children.Add(new UiaElement(child));
        }
        catch (Exception) { /* a shorter batch is reported as truncated by the walk */ }
        return children;
    }

    public void Invoke() => Pattern<InvokePattern>(InvokePattern.Pattern, "Invoke").Invoke();

    public void Step(bool increment)
    {
        var range = Pattern<RangeValuePattern>(RangeValuePattern.Pattern, increment ? "Increment" : "Decrement");
        var current = range.Current;
        if (!(current.SmallChange > 0)) // a step of zero would "complete" without any effect
            throw new UnsupportedActionException($"{(increment ? "Increment" : "Decrement")} (the element reports no small change)");
        var next = current.Value + (increment ? current.SmallChange : -current.SmallChange);
        range.SetValue(Math.Clamp(next, current.Minimum, current.Maximum));
    }

    public void SetValue(string text) => Pattern<ValuePattern>(ValuePattern.Pattern, "SetValue").SetValue(text);

    private bool Has(AutomationPattern pattern) => element.TryGetCurrentPattern(pattern, out _);

    private T Pattern<T>(AutomationPattern pattern, string action) where T : BasePattern =>
        element.TryGetCurrentPattern(pattern, out var found) ? (T)found : throw new UnsupportedActionException(action);

    private static T? Try<T>(Func<T> read)
    {
        try { return read(); }
        catch (Exception) { return default; }
    }
}
