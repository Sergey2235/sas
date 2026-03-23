/// <summary>
/// Запрос на анализ репозитория
/// </summary>
public class GitRepoAnalysisRequest
{
    /// <summary>
    /// URL репозитория (GitHub или GitLab)
    /// </summary>
    public string RepositoryUrl { get; set; } = "";
    
    /// <summary>
    /// Путь к файлу или директории внутри репозитория (опционально)
    /// </summary>
    public string? Path { get; set; }
    
    /// <summary>
    /// Ветка для анализа (опционально, по умолчанию main)
    /// </summary>
    public string? Branch { get; set; }
    
    /// <summary>
    /// Язык программирования (если не указан, определится автоматически)
    /// </summary>
    public string? Language { get; set; }
    
    /// <summary>
    /// Тип анализа
    /// </summary>
    public string AnalysisType { get; set; } = "Full";
    
    /// <summary>
    /// Personal Access Token для GitHub/GitLab
    /// </summary>
    public string? Token { get; set; }
    
    /// <summary>
    /// Применять исправления через коммит
    /// </summary>
    public bool ApplyFixes { get; set; } = false;
    
    /// <summary>
    /// Оставить комментарий к Pull Request / Merge Request
    /// </summary>
    public bool AddComment { get; set; } = false;
    
    /// <summary>
    /// Номер PR/MR (если нужно добавить комментарий к существующему PR)
    /// </summary>
    public int? PullRequestNumber { get; set; }
    
    /// <summary>
    /// Описание для MR/PR
    /// </summary>
    public string? Description { get; set; }
}

/// <summary>
/// Результат анализа репозитория
/// </summary>
public class GitRepoAnalysisResult
{
    public string RepositoryUrl { get; set; } = "";
    public string Owner { get; set; } = "";
    public string Repo { get; set; } = "";
    public string Branch { get; set; } = "";
    public string Path { get; set; } = "";
    public string Language { get; set; } = "";
    public List<GitFileInfo> Files { get; set; } = new();
    public string AnalysisResult { get; set; } = "";
    public DateTime AnalyzedAt { get; set; } = DateTime.Now;
    
    /// <summary>
    /// Результат применения исправлений (если запрошено)
    /// </summary>
    public GitCommitResult? FixResult { get; set; }
    
    /// <summary>
    /// Результат добавления комментария
    /// </summary>
    public bool CommentAdded { get; set; }
    public string? CommentUrl { get; set; }
}

/// <summary>
/// Запрос на валидацию токена
/// </summary>
public class TokenValidationRequest
{
    public string Platform { get; set; } = "github"; // github или gitlab
    public string Token { get; set; } = "";
}

/// <summary>
/// Результат валидации токена
/// </summary>
public class TokenValidationResult
{
    public bool IsValid { get; set; }
    public string? UserName { get; set; }
    public string? ErrorMessage { get; set; }
}
