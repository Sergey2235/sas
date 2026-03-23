public class CodeSubmission
{
    public string Code { get; set; } = string.Empty;
    public string Language { get; set; } = "C#";
    public string AnalysisType { get; set; } = "Full"; // ✅ Теперь строка, а не enum
    public int ComplexityLimit { get; set; } = 1000;
    public bool IncludeCodeExamples { get; set; } = true; // ✅ Новое: включать ли примеры улучшенного кода
}

public enum AnalysisType
{
    Full,           // Полный анализ
    SecurityOnly,   // Только безопасность
    StyleOnly,      // Только стиль
    Performance,    // Производительность
    BestPractices,  // Лучшие практики
    CodeExamples    // Только примеры улучшенного кода
}