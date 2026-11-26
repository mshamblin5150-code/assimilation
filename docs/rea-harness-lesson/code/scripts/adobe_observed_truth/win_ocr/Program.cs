// Reads one PNG path per stdin line; writes one JSON line per image:
// {"words":[{"text":"Radius","x":12,"y":40,"w":38,"h":11,"line":0}],"error":null}
// Coordinates are in the image's pixels. Images are read, never changed.
using System.Text.Json;
using Windows.Graphics.Imaging;
using Windows.Media.Ocr;
using Windows.Storage;
using Windows.Storage.Streams;

var engine = OcrEngine.TryCreateFromUserProfileLanguages();
string? path;
while ((path = Console.ReadLine()) is not null)
{
    path = path.Trim();
    if (path.Length == 0) continue;
    object answer;
    try
    {
        if (engine is null) throw new InvalidOperationException("No OCR language is installed for this user");
        var file = await StorageFile.GetFileFromPathAsync(path);
        using IRandomAccessStream stream = await file.OpenAsync(FileAccessMode.Read);
        var decoder = await BitmapDecoder.CreateAsync(stream);
        using var bitmap = await decoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Premultiplied);
        var result = await engine.RecognizeAsync(bitmap);
        var words = result.Lines.SelectMany((line, index) => line.Words.Select(word => new
        {
            text = word.Text,
            x = (int)Math.Round(word.BoundingRect.X),
            y = (int)Math.Round(word.BoundingRect.Y),
            w = (int)Math.Round(word.BoundingRect.Width),
            h = (int)Math.Round(word.BoundingRect.Height),
            line = index,
        })).ToArray();
        answer = new { words, error = (string?)null };
    }
    catch (Exception error)
    {
        answer = new { words = Array.Empty<object>(), error = error.Message };
    }
    Console.WriteLine(JsonSerializer.Serialize(answer));
    Console.Out.Flush();
}
