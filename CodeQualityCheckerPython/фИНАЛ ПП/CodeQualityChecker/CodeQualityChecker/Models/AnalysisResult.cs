public class AnalysisResult
{
    public List<string> Errors { get; set; } = new List<string>();
    public List<string> StyleIssues { get; set; } = new List<string>();
    public List<string> SecurityRisks { get; set; } = new List<string>();
    public List<string> BestPractices { get; set; } = new List<string>();
    public List<string> PerformanceIssues { get; set; } = new List<string>();
    public List<string> ArchitectureIssues { get; set; } = new List<string>();
    public List<string> ImprovementSuggestions { get; set; } = new List<string>();
    public List<string> CodeSuggestions { get; set; } = new List<string>(); // ✅ Новое: конкретные примеры улучшенного кода
    public string Language { get; set; } = "unknown";
    public string Summary { get; set; } = "";
    public int ComplexityScore { get; set; } = 0; // 0-10
    public int MaintainabilityScore { get; set; } = 0; // 0-10
    public int SecurityScore { get; set; } = 0; // 0-10
    public int PerformanceScore { get; set; } = 0; // 0-10
}