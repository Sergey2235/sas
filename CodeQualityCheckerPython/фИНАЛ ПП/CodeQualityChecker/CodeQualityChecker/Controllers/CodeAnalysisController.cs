using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
public class CodeAnalysisController : ControllerBase
{
    private readonly LlmService _llmService;
    private readonly AnalysisHistoryService _historyService;

    public CodeAnalysisController(LlmService llmService, AnalysisHistoryService historyService)
    {
        _llmService = llmService;
        _historyService = historyService;
    }

    [HttpPost("analyze")]
    public async Task<IActionResult> Analyze([FromBody] CodeSubmission submission)
    {
        try
        {
            if (submission == null || string.IsNullOrEmpty(submission.Code))
            {
                return BadRequest("Код не может быть пустым");
            }

            // Проверка размера кода (увеличен до 200KB)
            if (submission.Code.Length > 200000) // 200KB
            {
                return BadRequest("Код слишком большой для анализа. Максимальный размер: 200KB");
            }

            // Преобразуем строку в enum
            if (!Enum.TryParse<AnalysisType>(submission.AnalysisType, true, out var analysisType))
            {
                analysisType = AnalysisType.Full; // Значение по умолчанию
            }

            var result = await _llmService.AnalyzeCodeAsync(submission, analysisType);

            // Сохранение в историю
            await _historyService.SaveAnalysisAsync(
                submission.Code,
                submission.Language,
                result,
                GetUserId()
            );

            return Content(result, "application/json");
        }
        catch (Exception ex)
        {
            return StatusCode(500, $"Ошибка анализа: {ex.Message}");
        }
    }

    [HttpGet("history")]
    public async Task<IActionResult> GetHistory([FromQuery] int limit = 20)
    {
        var history = await _historyService.GetHistoryAsync(GetUserId(), limit);
        return Ok(history);
    }

    [HttpGet("history/{id:int}")]
    public async Task<IActionResult> GetHistoryItem(int id)
    {
        var item = (await _historyService.GetHistoryAsync(GetUserId()))
            .FirstOrDefault(h => h.Id == id);

        if (item == null) return NotFound();
        return Ok(item);
    }

    private string GetUserId()
    {
        // В реальном приложении здесь должна быть реализована аутентификация
        return User.Identity?.Name ?? "anonymous";
    }
}