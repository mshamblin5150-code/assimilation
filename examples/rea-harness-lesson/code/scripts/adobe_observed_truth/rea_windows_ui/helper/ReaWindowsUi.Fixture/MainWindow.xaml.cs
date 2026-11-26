using System.Windows;

namespace ReaWindowsUi.Fixture;

public partial class MainWindow : Window
{
    public MainWindow() => InitializeComponent();

    // The press is visible in the next capture: the button's name changes.
    private void OnPress(object sender, RoutedEventArgs e)
    {
        PressButton.Content = "Pressed";
        System.Windows.Automation.AutomationProperties.SetName(PressButton, "Pressed");
    }
}
