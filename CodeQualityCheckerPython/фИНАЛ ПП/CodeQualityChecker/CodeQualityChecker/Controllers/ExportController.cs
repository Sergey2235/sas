using Microsoft.AspNetCore.Mvc;
using Newtonsoft.Json;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

[ApiController]
[Route("api/[controller]")]
public class ExportController : ControllerBase
{
    private readonly AnalysisHistoryService _historyService;

    public ExportController(AnalysisHistoryService historyService)
    {
        _historyService = historyService;
    }

    [HttpGet("pdf/{id:int}")]
    public async Task<IActionResult> ExportToPdf(int id)
    {
        var item = (await _historyService.GetHistoryAsync()).FirstOrDefault(h => h.Id == id);
        if (item == null) return NotFound();

        var result = JsonConvert.DeserializeObject<AnalysisResult>(item.Result);

        // ✅ Используем правильный тип IDocument из QuestPDF.Infrastructure
        QuestPDF.Infrastructure.IDocument document = Document.Create(container =>
        {
            container.Page(page =>
            {
                page.Size(PageSizes.A4);
                page.Margin(2, Unit.Centimetre);
                page.PageColor(Colors.White);
                page.DefaultTextStyle(x => x.FontSize(12));

                page.Header().Text($"Анализ кода на {item.Language}").FontSize(20).Bold();
                page.Header().Text($"Дата: {item.Timestamp:dd.MM.yyyy HH:mm:ss}").FontSize(10);

                page.Content().Column(column =>
                {
                    column.Item().Text("Исходный код:").Bold().FontSize(14);
                    column.Item().Text(item.Code).FontSize(10);

                    column.Item().PaddingTop(10).Text("Результаты анализа:").Bold().FontSize(14);

                    foreach (var section in new[]
                    {
                        ("Ошибки", result.Errors),
                        ("Проблемы стиля", result.StyleIssues),
                        ("Риски безопасности", result.SecurityRisks),
                        ("Рекомендации", result.BestPractices)
                    })
                    {
                        if (section.Item2.Any())
                        {
                            column.Item().PaddingTop(5).Text(section.Item1).Bold();
                            foreach (var issue in section.Item2)
                            {
                                column.Item().Text($"• {issue}");
                            }
                        }
                    }

                    column.Item().PaddingTop(10).Text($"Сложность: {result.ComplexityScore}/10").FontSize(12);
                    column.Item().Text($"Сопровождаемость: {result.MaintainabilityScore}/10").FontSize(12);
                    column.Item().Text($"Безопасность: {result.SecurityScore}/10").FontSize(12);
                    column.Item().Text($"Производительность: {result.PerformanceScore}/10").FontSize(12);
                    column.Item().Text($"Резюме: {result.Summary}");
                });

                page.Footer().AlignCenter().Text(text =>
                {
                    text.DefaultTextStyle(x => x.FontSize(10));
                    text.Span("Сгенерировано ");
                    text.Span("Code Quality Checker").SemiBold();
                    text.Span(" с использованием LLM");
                });
            });
        });

        using var stream = new MemoryStream();
        document.GeneratePdf(stream); // ✅ Теперь метод GeneratePdf доступен
        var pdfBytes = stream.ToArray();

        return File(pdfBytes, "application/pdf", $"analysis_{id}_{DateTime.Now:yyyyMMddHHmmss}.pdf");
    }

    [HttpGet("html/{id:int}")]
    public async Task<IActionResult> ExportToHtml(int id)
    {
        var item = (await _historyService.GetHistoryAsync()).FirstOrDefault(h => h.Id == id);
        if (item == null) return NotFound();

        var result = JsonConvert.DeserializeObject<AnalysisResult>(item.Result);

        var html = $@"
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset='utf-8'>
            <title>Отчет анализа #{id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section {{ margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class='header'>
                <h1>Отчет анализа кода #{id}</h1>
                <p>Язык: {item.Language} | Дата: {item.Timestamp:dd.MM.yyyy HH:mm:ss}</p>
            </div>
            <div class='section'>
                <h2>Результаты анализа</h2>
                <p>Содержимое отчета будет сгенерировано динамически.</p>
            </div>
        </body>
        </html>";

        return Content(html, "text/html", System.Text.Encoding.UTF8);
    }
}