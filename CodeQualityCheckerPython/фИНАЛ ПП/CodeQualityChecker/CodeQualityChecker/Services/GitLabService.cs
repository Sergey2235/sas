using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Newtonsoft.Json.Linq;

public class GitLabService
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _config;

    public GitLabService(HttpClient httpClient, IConfiguration config)
    {
        _httpClient = httpClient;
        _config = config;
    }

    /// <summary>
    /// Извлекает информацию о репозитории из GitLab URL
    /// </summary>
    public (string owner, string repo, string branch, string path) ParseGitLabUrl(string url)
    {
        url = url.TrimEnd('/');

        // Форматы URL:
        // https://gitlab.com/owner/repo
        // https://gitlab.com/owner/repo/-/tree/branch
        // https://gitlab.com/owner/repo/-/blob/branch/path/to/file

        var uri = new Uri(url);
        var pathSegments = uri.AbsolutePath.Trim('/').Split('/');

        if (pathSegments.Length < 2)
            throw new ArgumentException("Неверный формат URL GitLab репозитория");

        // Ищем позицию repo
        var repoIndex = 0;
        for (int i = 0; i < pathSegments.Length; i++)
        {
            if (pathSegments[i] != "-" && pathSegments[i] != "")
            {
                repoIndex = i;
                break;
            }
        }

        var owner = pathSegments[repoIndex];
        var repo = pathSegments[repoIndex + 1].Replace(".git", "");
        var branch = "main";
        var path = "";

        // Ищем tree или blob
        var treeIndex = -1;
        for (int i = 0; i < pathSegments.Length; i++)
        {
            if (pathSegments[i] == "tree")
            {
                treeIndex = i;
                if (i + 1 < pathSegments.Length)
                    branch = pathSegments[i + 1];
                break;
            }
            else if (pathSegments[i] == "blob")
            {
                treeIndex = i;
                if (i + 1 < pathSegments.Length)
                    branch = pathSegments[i + 1];
            }
        }

        if (treeIndex >= 0)
        {
            var pathStart = treeIndex + 2; // После tree/branch или blob/branch
            if (pathStart < pathSegments.Length)
            {
                path = string.Join("/", pathSegments.Skip(pathStart));
            }
        }

        return (owner, repo, branch, path);
    }

    /// <summary>
    /// Кодирует путь для GitLab API
    /// </summary>
    private string EncodeProjectPath(string owner, string repo)
    {
        return Uri.EscapeDataString($"{owner}/{repo}");
    }

    /// <summary>
    /// Получает содержимое файла из репозитория
    /// </summary>
    public async Task<string> GetFileContentAsync(string owner, string repo, string path, string branch, string? token = null)
    {
        var projectPath = EncodeProjectPath(owner, repo);
        var encodedPath = Uri.EscapeDataString(path);
        
        var url = $"https://gitlab.com/api/v4/projects/{projectPath}/repository/files/{encodedPath}?ref={branch}";
        
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        
        if (!string.IsNullOrEmpty(token))
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JObject.Parse(await response.Content.ReadAsStringAsync());
        var content = json["content"]?.ToString();
        
        if (string.IsNullOrEmpty(content))
            throw new Exception("Не удалось получить содержимое файла");

        // Декодируем base64
        var decoded = Encoding.UTF8.GetString(Convert.FromBase64String(content));
        return decoded;
    }

    /// <summary>
    /// Получает список файлов в директории
    /// </summary>
    public async Task<List<GitFileInfo>> GetDirectoryContentsAsync(string owner, string repo, string path, string branch, string? token = null)
    {
        var projectPath = EncodeProjectPath(owner, repo);
        
        var url = string.IsNullOrEmpty(path)
            ? $"https://gitlab.com/api/v4/projects/{projectPath}/repository/tree?ref={branch}"
            : $"https://gitlab.com/api/v4/projects/{projectPath}/repository/tree?path={Uri.EscapeDataString(path)}&ref={branch}";

        var request = new HttpRequestMessage(HttpMethod.Get, url);
        
        if (!string.IsNullOrEmpty(token))
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JArray.Parse(await response.Content.ReadAsStringAsync());
        var files = new List<GitFileInfo>();

        foreach (var item in json)
        {
            files.Add(new GitFileInfo
            {
                Name = item["name"]?.ToString() ?? "",
                Path = item["path"]?.ToString() ?? "",
                Type = item["type"]?.ToString() ?? "blob",
                Size = 0
            });
        }

        return files;
    }

    /// <summary>
    /// Создает коммит с исправлениями и Merge Request
    /// </summary>
    public async Task<GitCommitResult> CreateCommitWithFixesAsync(
        string owner, string repo, string targetBranch,
        string filePath, string originalContent, string fixedContent,
        string commitMessage, string mrDescription, string? token = null)
    {
        if (string.IsNullOrEmpty(token))
            throw new ArgumentException("Требуется токен для создания коммита");

        var projectPath = EncodeProjectPath(owner, repo);
        var featureBranch = $"code-quality-fix-{DateTime.Now:yyyyMMddHHmmss}";

        // Создаем новую ветку
        await CreateBranchAsync(projectPath, featureBranch, targetBranch, token);

        // Создаем коммит с исправлением
        await CreateCommitAsync(projectPath, featureBranch, filePath, fixedContent, commitMessage, token);

        // Создаем Merge Request
        var mrIid = await CreateMergeRequestAsync(projectPath, featureBranch, targetBranch, commitMessage, mrDescription, token);

        return new GitCommitResult
        {
            Success = true,
            BranchName = featureBranch,
            PullRequestUrl = $"https://gitlab.com/{owner}/{repo}/-/merge_requests/{mrIid}",
            PullRequestNumber = mrIid
        };
    }

    /// <summary>
    /// Оставляет комментарий к Merge Request
    /// </summary>
    public async Task<bool> AddMergeRequestCommentAsync(
        string owner, string repo, int mrIid,
        string comment, string? token = null)
    {
        if (string.IsNullOrEmpty(token))
            throw new ArgumentException("Требуется токен для добавления комментария");

        var projectPath = EncodeProjectPath(owner, repo);
        
        var request = new HttpRequestMessage(HttpMethod.Post,
            $"https://gitlab.com/api/v4/projects/{projectPath}/merge_requests/{mrIid}/notes");
        
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Content = new StringContent(
            JsonSerializer.Serialize(new { body = comment }),
            Encoding.UTF8,
            "application/json");

        var response = await _httpClient.SendAsync(request);
        return response.IsSuccessStatusCode;
    }

    private async Task CreateBranchAsync(string projectPath, string branchName, string baseBranch, string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Post,
            $"https://gitlab.com/api/v4/projects/{projectPath}/repository/branches");
        
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Content = new StringContent(
            JsonSerializer.Serialize(new
            {
                branch = branchName,
                @ref = baseBranch
            }),
            Encoding.UTF8,
            "application/json");

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();
    }

    private async Task CreateCommitAsync(string projectPath, string branch, string path,
        string content, string message, string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Post,
            $"https://gitlab.com/api/v4/projects/{projectPath}/repository/commits");
        
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        
        var actions = new[]
        {
            new
            {
                action = "update",
                file_path = path,
                content = Convert.ToBase64String(Encoding.UTF8.GetBytes(content))
            }
        };

        var body = new
        {
            branch = branch,
            commit_message = message,
            actions = actions
        };

        request.Content = new StringContent(
            JsonSerializer.Serialize(body),
            Encoding.UTF8,
            "application/json");

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();
    }

    private async Task<int> CreateMergeRequestAsync(string projectPath,
        string sourceBranch, string targetBranch, string title, string description, string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Post,
            $"https://gitlab.com/api/v4/projects/{projectPath}/merge_requests");
        
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Content = new StringContent(
            JsonSerializer.Serialize(new
            {
                source_branch = sourceBranch,
                target_branch = targetBranch,
                title = title,
                description = description
            }),
            Encoding.UTF8,
            "application/json");

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JObject.Parse(await response.Content.ReadAsStringAsync());
        return json["iid"]?.Value<int>() ?? 0;
    }

    /// <summary>
    /// Проверяет валидность токена
    /// </summary>
    public async Task<bool> ValidateTokenAsync(string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Get, "https://gitlab.com/api/v4/user");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        return response.IsSuccessStatusCode;
    }

    /// <summary>
    /// Получает информацию о пользователе по токену
    /// </summary>
    public async Task<string> GetUserNameAsync(string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Get, "https://gitlab.com/api/v4/user");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JObject.Parse(await response.Content.ReadAsStringAsync());
        return json["username"]?.ToString() ?? "unknown";
    }

    /// <summary>
    /// Получает название ветки по умолчанию для репозитория
    /// </summary>
    public async Task<string> GetDefaultBranchAsync(string owner, string repo, string? token = null)
    {
        var projectPath = EncodeProjectPath(owner, repo);
        var request = new HttpRequestMessage(HttpMethod.Get, 
            $"https://gitlab.com/api/v4/projects/{projectPath}");
        
        if (!string.IsNullOrEmpty(token))
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JObject.Parse(await response.Content.ReadAsStringAsync());
        return json["default_branch"]?.ToString() ?? "main";
    }
}
