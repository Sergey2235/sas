using Microsoft.AspNetCore.Mvc;
using System.Text.RegularExpressions;

[ApiController]
[Route("api/[controller]")]
public class GitController : ControllerBase
{
    private readonly GitHubService _gitHubService;
    private readonly GitLabService _gitLabService;
    private readonly LlmService _llmService;
    private readonly AnalysisHistoryService _historyService;

    // Поддерживаемые расширения файлов
    private static readonly Dictionary<string, string> ExtensionToLanguage = new(StringComparer.OrdinalIgnoreCase)
    {
        { ".cs", "C#" }, { ".csx", "C#" },
        { ".py", "Python" }, { ".pyw", "Python" },
        { ".js", "JavaScript" },
        { ".ts", "TypeScript" }, { ".tsx", "TypeScript" },
        { ".jsx", "JavaScript" },
        { ".java", "Java" },
        { ".cpp", "C++" }, { ".cc", "C++" }, { ".cxx", "C++" }, { ".h", "C++" }, { ".hpp", "C++" },
        { ".c", "C" },
        { ".go", "Go" },
        { ".rs", "Rust" },
        { ".php", "PHP" },
        { ".rb", "Ruby" },
        { ".swift", "Swift" },
        { ".kt", "Kotlin" }, { ".kts", "Kotlin" },
        { ".sql", "SQL" },
        { ".m", "Objective-C" }, { ".mm", "Objective-C" }
    };

    public GitController(
        GitHubService gitHubService,
        GitLabService gitLabService,
        LlmService llmService,
        AnalysisHistoryService historyService)
    {
        _gitHubService = gitHubService;
        _gitLabService = gitLabService;
        _llmService = llmService;
        _historyService = historyService;
    }

    [HttpPost("validate-token")]
    public async Task<IActionResult> ValidateToken([FromBody] TokenValidationRequest request)
    {
        try
        {
            if (string.IsNullOrEmpty(request.Token))
            {
                return BadRequest(new TokenValidationResult 
                { 
                    IsValid = false, 
                    ErrorMessage = "Токен не предоставлен" 
                });
            }

            if (request.Platform.ToLower() == "github")
            {
                var isValid = await _gitHubService.ValidateTokenAsync(request.Token);
                if (isValid)
                {
                    var userName = await _gitHubService.GetUserNameAsync(request.Token);
                    return Ok(new TokenValidationResult { IsValid = true, UserName = userName });
                }
                return Ok(new TokenValidationResult { IsValid = false, ErrorMessage = "Неверный токен GitHub" });
            }
            else if (request.Platform.ToLower() == "gitlab")
            {
                var isValid = await _gitLabService.ValidateTokenAsync(request.Token);
                if (isValid)
                {
                    var userName = await _gitLabService.GetUserNameAsync(request.Token);
                    return Ok(new TokenValidationResult { IsValid = true, UserName = userName });
                }
                return Ok(new TokenValidationResult { IsValid = false, ErrorMessage = "Неверный токен GitLab" });
            }

            return BadRequest(new TokenValidationResult { IsValid = false, ErrorMessage = "Неизвестная платформа" });
        }
        catch (Exception ex)
        {
            return StatusCode(500, new TokenValidationResult 
            { 
                IsValid = false, 
                ErrorMessage = ex.Message 
            });
        }
    }

    [HttpPost("analyze-repo")]
    public async Task<IActionResult> AnalyzeRepository([FromBody] GitRepoAnalysisRequest request)
    {
        try
        {
            if (string.IsNullOrEmpty(request.RepositoryUrl))
            {
                return BadRequest("URL репозитория обязателен");
            }

            // Определяем платформу
            var platform = DetectPlatform(request.RepositoryUrl);
            if (platform == null)
            {
                return BadRequest("Неверный URL репозитория. Поддерживаются GitHub и GitLab.");
            }

            // Парсим URL и получаем информацию о репозитории
            string owner, repo, branch, path;
            
            if (platform == "github")
            {
                (owner, repo, branch, path) = _gitHubService.ParseGitHubUrl(request.RepositoryUrl);
            }
            else
            {
                (owner, repo, branch, path) = _gitLabService.ParseGitLabUrl(request.RepositoryUrl);
            }

            // Если ветка не указана, получаем default branch из GitHub
            if (string.IsNullOrEmpty(request.Branch))
            {
                try
                {
                    if (platform == "github")
                    {
                        branch = await _gitHubService.GetDefaultBranchAsync(owner, repo, request.Token);
                    }
                    else
                    {
                        branch = await _gitLabService.GetDefaultBranchAsync(owner, repo, request.Token);
                    }
                }
                catch
                {
                    // Если не удалось получить - используем значение по умолчанию
                    branch = string.IsNullOrEmpty(branch) ? "main" : branch;
                }
            }
            else
            {
                branch = request.Branch;
            }

            path = request.Path ?? path;
            path = request.Path ?? path;

            // Получаем список файлов
            List<GitFileInfo> files;
            if (platform == "github")
            {
                files = await _gitHubService.GetDirectoryContentsAsync(owner, repo, path, branch, request.Token);
            }
            else
            {
                files = await _gitLabService.GetDirectoryContentsAsync(owner, repo, path, branch, request.Token);
            }

            // Фильтруем только файлы с поддерживаемыми расширениями
            var codeFiles = files
                .Where(f => f.Type == "file" && ExtensionToLanguage.Keys.Any(ext => f.Name.EndsWith(ext, StringComparison.OrdinalIgnoreCase)))
                .ToList();

            if (!codeFiles.Any())
            {
                return BadRequest("В указанной директории не найдены файлы с поддерживаемыми расширениями");
            }

            // Ограничиваем количество файлов для анализа
            var filesToAnalyze = codeFiles.Take(10).ToList();

            // Анализируем каждый файл
            var analysisResults = new List<string>();
            var detectedLanguage = request.Language ?? "C#";

            foreach (var file in filesToAnalyze)
            {
                string content;
                if (platform == "github")
                {
                    content = await _gitHubService.GetFileContentAsync(owner, repo, file.Path, branch, request.Token);
                }
                else
                {
                    content = await _gitLabService.GetFileContentAsync(owner, repo, file.Path, branch, request.Token);
                }

                // Определяем язык файла
                var ext = Path.GetExtension(file.Name);
                var fileLanguage = ExtensionToLanguage.GetValueOrDefault(ext, detectedLanguage);

                // Анализируем через LLM
                var submission = new CodeSubmission
                {
                    Code = content,
                    Language = fileLanguage,
                    AnalysisType = request.AnalysisType
                };

                if (!Enum.TryParse<AnalysisType>(request.AnalysisType, true, out var analysisType))
                {
                    analysisType = AnalysisType.Full;
                }

                var result = await _llmService.AnalyzeCodeAsync(submission, analysisType);
                
                analysisResults.Add($"### Файл: {file.Path} ({fileLanguage})\n\n{result}");
            }

            // Формируем итоговый результат
            var fullAnalysis = $"## Анализ репозитория {owner}/{repo}\n" +
                              $"Ветка: {branch}\n" +
                              $"Путь: {path}\n" +
                              $"Проанализировано файлов: {filesToAnalyze.Count}\n\n" +
                              string.Join("\n\n---\n\n", analysisResults);

            var resultObj = new GitRepoAnalysisResult
            {
                RepositoryUrl = request.RepositoryUrl,
                Owner = owner,
                Repo = repo,
                Branch = branch,
                Path = path,
                Language = detectedLanguage,
                Files = filesToAnalyze,
                AnalysisResult = fullAnalysis,
                AnalyzedAt = DateTime.Now
            };

            // Применяем исправления, если запрошено
            if (request.ApplyFixes && !string.IsNullOrEmpty(request.Token))
            {
                var fixResult = await ApplyFixesAsync(platform, owner, repo, branch, request, analysisResults);
                resultObj.FixResult = fixResult;
            }

            // Добавляем комментарий к PR/MR, если запрошено
            if (request.AddComment && !string.IsNullOrEmpty(request.Token) && request.PullRequestNumber.HasValue)
            {
                var commentAdded = await AddCommentToPullRequestAsync(
                    platform, owner, repo, request.PullRequestNumber.Value, 
                    fullAnalysis, request.Token);
                
                resultObj.CommentAdded = commentAdded;
                resultObj.CommentUrl = commentAdded 
                    ? (platform == "github" 
                        ? $"https://github.com/{owner}/{repo}/pull/{request.PullRequestNumber}" 
                        : $"https://gitlab.com/{owner}/{repo}/-/merge_requests/{request.PullRequestNumber}")
                    : null;
            }

            // Сохраняем в историю
            await _historyService.SaveAnalysisAsync(
                $"Git: {owner}/{repo}/{path}",
                detectedLanguage,
                fullAnalysis,
                "git-analysis"
            );

            return Ok(resultObj);
        }
        catch (Exception ex)
        {
            return StatusCode(500, $"Ошибка при анализе репозитория: {ex.Message}");
        }
    }

    [HttpPost("analyze-file")]
    public async Task<IActionResult> AnalyzeSingleFile([FromBody] GitRepoAnalysisRequest request)
    {
        try
        {
            if (string.IsNullOrEmpty(request.RepositoryUrl))
            {
                return BadRequest("URL репозитория обязателен");
            }

            var platform = DetectPlatform(request.RepositoryUrl);
            if (platform == null)
            {
                return BadRequest("Неверный URL репозитория");
            }

            string owner, repo, branch, path;
            
            if (platform == "github")
            {
                (owner, repo, branch, path) = _gitHubService.ParseGitHubUrl(request.RepositoryUrl);
            }
            else
            {
                (owner, repo, branch, path) = _gitLabService.ParseGitLabUrl(request.RepositoryUrl);
            }

            // Если путь к файлу не указан, пытаемся определить из URL
            if (string.IsNullOrEmpty(path) && !string.IsNullOrEmpty(request.Path))
            {
                path = request.Path;
            }

            branch = request.Branch ?? branch;

            if (string.IsNullOrEmpty(path))
            {
                return BadRequest("Укажите путь к файлу");
            }

            // Получаем содержимое файла
            string content;
            if (platform == "github")
            {
                content = await _gitHubService.GetFileContentAsync(owner, repo, path, branch, request.Token);
            }
            else
            {
                content = await _gitLabService.GetFileContentAsync(owner, repo, path, branch, request.Token);
            }

            // Определяем язык
            var ext = Path.GetExtension(path);
            var language = request.Language ?? ExtensionToLanguage.GetValueOrDefault(ext, "C#");

            // Анализируем
            var submission = new CodeSubmission
            {
                Code = content,
                Language = language,
                AnalysisType = request.AnalysisType
            };

            if (!Enum.TryParse<AnalysisType>(request.AnalysisType, true, out var analysisType))
            {
                analysisType = AnalysisType.Full;
            }

            var result = await _llmService.AnalyzeCodeAsync(submission, analysisType);

            return Ok(new
            {
                RepositoryUrl = request.RepositoryUrl,
                Owner = owner,
                Repo = repo,
                Branch = branch,
                FilePath = path,
                Language = language,
                Content = content,
                AnalysisResult = result
            });
        }
        catch (Exception ex)
        {
            return StatusCode(500, $"Ошибка при анализе файла: {ex.Message}");
        }
    }

    private string? DetectPlatform(string url)
    {
        if (url.Contains("github.com", StringComparison.OrdinalIgnoreCase))
            return "github";
        if (url.Contains("gitlab.com", StringComparison.OrdinalIgnoreCase))
            return "gitlab";
        return null;
    }

    private async Task<GitCommitResult> ApplyFixesAsync(
        string platform, string owner, string repo, string branch,
        GitRepoAnalysisRequest request, List<string> analysisResults)
    {
        try
        {
            // Для простоты - создаем один коммит с описанием проблем
            var commitMessage = $"Code Quality: исправления от Code Quality Checker\n\n{request.Description ?? "Автоматические исправления качества кода"}";
            var description = $"## Результаты анализа\n\n{string.Join("\n\n---\n\n", analysisResults.Take(3))}";

            if (platform == "github")
            {
                return await _gitHubService.CreateCommitWithFixesAsync(
                    owner, repo, branch,
                    request.Path ?? "README.md",
                    "Analysis result",
                    $"# Analysis Result\n\n{DateTime.Now}\n\n{description}",
                    commitMessage,
                    description,
                    request.Token);
            }
            else
            {
                return await _gitLabService.CreateCommitWithFixesAsync(
                    owner, repo, branch,
                    request.Path ?? "README.md",
                    "Analysis result",
                    $"# Analysis Result\n\n{DateTime.Now}\n\n{description}",
                    commitMessage,
                    description,
                    request.Token);
            }
        }
        catch (Exception ex)
        {
            return new GitCommitResult
            {
                Success = false,
                ErrorMessage = ex.Message
            };
        }
    }

    private async Task<bool> AddCommentToPullRequestAsync(
        string platform, string owner, string repo, int prNumber,
        string analysisResult, string token)
    {
        try
        {
            var comment = $"## 📊 Результат анализа кода\n\n" +
                         $"Анализ выполнен автоматически с помощью **Code Quality Checker**\n\n" +
                         $"{analysisResult}\n\n" +
                         $"_Этот комментарий добавлен автоматически_";

            if (platform == "github")
            {
                return await _gitHubService.AddPullRequestCommentAsync(owner, repo, prNumber, comment, token);
            }
            else
            {
                return await _gitLabService.AddMergeRequestCommentAsync(owner, repo, prNumber, comment, token);
            }
        }
        catch
        {
            return false;
        }
    }
}
