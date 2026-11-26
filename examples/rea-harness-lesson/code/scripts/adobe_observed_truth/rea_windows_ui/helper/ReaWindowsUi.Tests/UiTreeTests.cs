// Seam 3: the accessibility tree walk, against a fake element tree. Behaviour mirrors REA 6.8.0's
// Swift helper (bridge/native/ReaNativeUI.swift, the `pending` depth-first walk).
using ReaWindowsUi;

namespace ReaWindowsUi.Tests;

/// <summary>An in-memory element: role, title, value, actions and children are given.</summary>
public sealed class FakeElement(string role, params FakeElement[] children) : IUiElement
{
    public string? Role { get; } = role;
    public string? Title { get; init; }
    public object? Value { get; init; }
    public IReadOnlyList<string> Actions { get; init; } = [];
    public bool CountUnavailable { get; init; }
    public int ProcessId => OwnerUnreadable ? throw new InvalidOperationException("element is gone") : Owner;
    public int Owner { get; init; } = 4242;
    public bool OwnerUnreadable { get; init; }
    public Exception? ActionThrows { get; init; }
    public List<string> Performed { get; } = [];

    public int? ChildCount() => CountUnavailable ? null : children.Length;
    public IReadOnlyList<IUiElement> Children(int count) => children.Take(count).ToArray();
    public void Invoke() => Perform("Invoke");
    public void Step(bool increment) => Perform(increment ? "Increment" : "Decrement");
    public void SetValue(string text) => Perform($"SetValue:{text}");

    private void Perform(string action)
    {
        if (ActionThrows is not null) throw ActionThrows;
        if (!Actions.Contains(action.Split(':')[0])) throw new UnsupportedActionException(action);
        Performed.Add(action);
    }
}

public class UiTreeTests
{
    [Fact]
    public void Nodes_are_captured_depth_first_with_child_index_paths()
    {
        var window = new FakeElement("Window", new FakeElement("Pane", new FakeElement("Button")), new FakeElement("Edit"));

        var capture = UiTree.Capture(window, maxNodes: 500);

        Assert.Equal(["", "0", "0.0", "1"], capture.Nodes.Select(n => string.Join(".", n.Path)));
    }

    [Fact]
    public void The_node_budget_cuts_the_walk_and_says_so()
    {
        var window = new FakeElement("Window", new FakeElement("Button"), new FakeElement("Edit"), new FakeElement("Edit"));

        var capture = UiTree.Capture(window, maxNodes: 2);

        Assert.Equal((2, true), (capture.Nodes.Count, capture.Truncated));
    }

    [Fact]
    public void An_unreadable_child_count_is_a_gap_not_a_silent_omission()
    {
        var window = new FakeElement("Window", new FakeElement("Pane") { CountUnavailable = true });

        var capture = UiTree.Capture(window, maxNodes: 500);

        Assert.Equal((true, "UI Automation child count unavailable at path [0]"), (capture.Truncated, capture.Gaps.Single()));
    }
}

public class UiActionTests
{
    private static readonly FakeElement Ok = new("Button") { Actions = ["Invoke"] };
    private static readonly FakeElement Slider = new("Slider") { Actions = ["Increment", "Decrement"] };
    private static readonly FakeElement Field = new("Edit") { Actions = ["SetValue"] };

    private static FakeElement Window() => new("Window", new FakeElement("Pane", Ok, Slider, Field));

    [Fact]
    public void Click_invokes_the_element_at_the_path()
    {
        var button = new FakeElement("Button") { Actions = ["Invoke"] };
        var window = new FakeElement("Window", new FakeElement("Pane", button));

        UiActions.Perform(window, new UiAction("click", [0, 0], null, null), expectedProcessId: 4242);

        Assert.Equal(["Invoke"], button.Performed);
    }

    [Fact]
    public void Scroll_steps_a_range_value_up_or_down()
    {
        var slider = new FakeElement("Slider") { Actions = ["Increment", "Decrement"] };
        var window = new FakeElement("Window", slider);

        UiActions.Perform(window, new UiAction("scroll", [0], "decrement", null), expectedProcessId: 4242);

        Assert.Equal(["Decrement"], slider.Performed);
    }

    [Fact]
    public void Key_entry_sets_the_value_of_the_element()
    {
        var field = new FakeElement("Edit") { Actions = ["SetValue"] };
        var window = new FakeElement("Window", field);

        UiActions.Perform(window, new UiAction("key-entry", [0], null, "12"), expectedProcessId: 4242);

        Assert.Equal(["SetValue:12"], field.Performed);
    }

    [Fact]
    public void An_element_that_cannot_do_the_action_fails_with_no_fallback()
    {
        var label = new FakeElement("Text");
        var window = new FakeElement("Window", label);

        var failure = Assert.Throws<HelperFailure>(
            () => UiActions.Perform(window, new UiAction("click", [0], null, null), expectedProcessId: 4242));

        Assert.Equal(("action-failed", 0), (failure.Code, label.Performed.Count));
    }

    [Fact]
    public void A_path_that_no_longer_exists_is_element_missing()
    {
        var failure = Assert.Throws<HelperFailure>(
            () => UiActions.Perform(Window(), new UiAction("click", [0, 9], null, null), expectedProcessId: 4242));

        Assert.Equal("element-missing", failure.Code);
    }

    [Fact]
    public void An_element_owned_by_another_process_is_refused()
    {
        var foreign = new FakeElement("Button") { Actions = ["Invoke"], Owner = 1 };
        var window = new FakeElement("Window", foreign);

        var failure = Assert.Throws<HelperFailure>(
            () => UiActions.Perform(window, new UiAction("click", [0], null, null), expectedProcessId: 4242));

        Assert.Equal(("element-owner-mismatch", 0), (failure.Code, foreign.Performed.Count));
    }

    [Fact]
    public void Any_failure_inside_the_action_is_action_failed_as_on_macos()
    {
        var disabled = new FakeElement("Button") { Actions = ["Invoke"], ActionThrows = new InvalidOperationException("not enabled") };
        var window = new FakeElement("Window", disabled);

        var failure = Assert.Throws<HelperFailure>(
            () => UiActions.Perform(window, new UiAction("click", [0], null, null), expectedProcessId: 4242));

        Assert.Equal("action-failed", failure.Code);
    }

    [Fact]
    public void An_element_whose_owner_cannot_be_read_is_an_owner_mismatch()
    {
        var gone = new FakeElement("Button") { Actions = ["Invoke"], OwnerUnreadable = true };
        var window = new FakeElement("Window", gone);

        var failure = Assert.Throws<HelperFailure>(
            () => UiActions.Perform(window, new UiAction("click", [0], null, null), expectedProcessId: 4242));

        Assert.Equal("element-owner-mismatch", failure.Code);
    }
}

public class UiValueTests
{
    [Fact]
    public void A_value_that_is_not_a_finite_number_is_a_gap_not_a_silent_null()
    {
        var window = new FakeElement("Window", new FakeElement("Slider") { Value = double.NaN });

        var capture = UiTree.Capture(window, maxNodes: 500);

        Assert.Equal((true, "UI Automation value is not a finite number at path [0]"), (capture.Truncated, capture.Gaps.Single()));
    }
}