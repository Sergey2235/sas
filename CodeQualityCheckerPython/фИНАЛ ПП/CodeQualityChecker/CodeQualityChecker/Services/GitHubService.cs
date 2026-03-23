using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Newtonsoft.Json.Linq;

public class GitHubService
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _config;

    public GitHubService(HttpClient httpClient, IConfiguration config)
    {
        _httpClient = httpClient;
        _config = config;
    }

    public (string owner, string repo, string branch, string path) ParseGitHubUrl(string url)
    {
        url = url.TrimEnd('/');
        var uri = new Uri(url);
        var segments = uri.Segments.Skip(1).ToArray();

        if (segments.Length < 2)
            throw new ArgumentException("Неверный формат URL GitHub репозитория");

        var owner = segments[0].TrimEnd('/');
        var repo = segments[1].TrimEnd('/').Replace(".git", "");
        var branch = "";
        var path = "";

        var pathIndex = -1;
        for (int i = 2; i < segments.Length; i++)
        {
            var segment = segments[i].TrimEnd('/');
            if (segment == "tree")
            {
                pathIndex = i + 1;
                if (pathIndex < segments.Length)
                    branch = segments[pathIndex].TrimEnd('/');
                break;
            }
            else if (segment == "blob")
            {
                pathIndex = i + 2;
                if (pathIndex < segments.Length)
                    branch = segments[pathIndex - 1].TrimEnd('/');
                break;
            }
        }

        if (pathIndex >= 0 && pathIndex < segments.Length)
        {
            var pathSegments = segments.Skip(pathIndex).Select(s => s.TrimEnd('/'));
            path = string.Join("/", pathSegments);
        }

        return (owner, repo, branch, path);
    }

    public async Task<string> GetDefaultBranchAsync(string owner, string repo, string? token = null)
    {
        var request = new HttpRequestMessage(HttpMethod.Get,
            $"https://api.github.com/repos/{owner}/{repo}");
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        
        if (!string.IsNullOrEmpty(token))
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JObject.Parse(await response.Content.ReadAsStringAsync());
        return json["default_branch"]?.ToString() ?? "main";
    }

    public async Task<string> GetFileContentAsync(string owner, string repo, string path, string branch, string? token = null)
    {
        var request = new HttpRequestMessage(HttpMethod.Get, 
            $"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}");
        
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        
        if (!string.IsNullOrEmpty(token))
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JObject.Parse(await response.Content.ReadAsStringAsync());
        var content = json["content"]?.ToString();
        
        if (string.IsNullOrEmpty(content))
            throw new Exception("Не удалось получить содержимое файла");

        var decoded = Encoding.UTF8.GetString(Convert.FromBase64String(content.Replace("\n", "")));
        return decoded;
    }

    public async Task<List<GitFileInfo>> GetDirectoryContentsAsync(string owner, string repo, string path, string branch, string? token = null)
    {
        var url = string.IsNullOrEmpty(path)
            ? $"https://api.github.com/repos/{owner}/{repo}/contents?ref={branch}"
            : $"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}";

        var request = new HttpRequestMessage(HttpMethod.Get, url);
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        
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
                Type = item["type"]?.ToString() ?? "file",
                Size = item["size"]?.Value<long>() ?? 0,
                DownloadUrl = item["download_url"]?.ToString()
            });
        }

        return files;
    }

    public async Task<GitCommitResult> CreateCommitWithFixesAsync(
        string owner, string repo, string branch,
        string filePath, string originalContent, string fixedContent,
        string commitMessage, string prDescription, string? token = null)
    {
        if (string.IsNullOrEmpty(token))
            throw new ArgumentException("Требуется токен для создания коммита");

        var branchInfo = await GetBranchInfoAsync(owner, repo, branch, token);
        var sha = branchInfo["commit"]?["sha"]?.ToString();

        if (string.IsNullOrEmpty(sha))
            throw new Exception("Не удалось получить информацию о ветке");

        var featureBranch = $"code-quality-fix-{DateTime.Now:yyyyMMddHHmmss}";
        await CreateBranchAsync(owner, repo, featureBranch, sha, token);
        await UpdateFileAsync(owner, repo, filePath, fixedContent, commitMessage, featureBranch, token);

        var prNumber = await CreatePullRequestAsync(owner, repo, featureBranch, branch, commitMessage, prDescription, token);

        return new GitCommitResult
        {
            Success = true,
            BranchName = featureBranch,
            PullRequestUrl = $"https://github.com/{owner}/{repo}/pull/{prNumber}",
            PullRequestNumber = prNumber
        };
    }

    public async Task<bool> AddPullRequestCommentAsync(string owner, string repo, int prNumber, string comment, string? token = null)
    {
        if (string.IsNullOrEmpty(token))
            throw new ArgumentException("Требуется токен");

        var request = new HttpRequestMessage(HttpMethod.Post,
            $"https://api.github.com/repos/{owner}/{repo}/issues/{prNumber}/comments");
        
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Content = new StringContent(
            JsonSerializer.Serialize(new { body = comment }),
            Encoding.UTF8, "application/json");

        var response = await _httpClient.SendAsync(request);
        return response.IsSuccessStatusCode;
    }

    private async Task<JObject> GetBranchInfoAsync(string owner, string repo, string branch, string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Get,
            $"https://api.github.com/repos/{owner}/{repo}/branches/{branch}");
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        return JObject.Parse(await response.Content.ReadAsStringAsync());
    }

    private async Task CreateBranchAsync(string owner, string repo, string branchName, string sha, string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Post,
            $"https://api.github.com/repos/{owner}/{repo}/git/refs");
        
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Content = new StringContent(
            JsonSerializer.Serialize(new { @ref = $"refs/heads/{branchName}", sha = sha }),
            Encoding.UTF8, "application/json");

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();
    }

    private async Task UpdateFileAsync(string owner, string repo, string path, string newContent, string message, string branch, string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Put,
            $"https://api.github.com/repos/{owner}/{repo}/contents/{path}");
        
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        
        var body = new
        {
            message = message,
            content = Convert.ToBase64String(Encoding.UTF8.GetBytes(newContent)),
            branch = branch
        };

        request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();
    }

    private async Task<int> CreatePullRequestAsync(string owner, string repo, string head, string base_, string title, string body, string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Post,
            $"https://api.github.com/repos/{owner}/{repo}/pulls");
        
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Content = new StringContent(
            JsonSerializer.Serialize(new { head, base_, title, body }),
            Encoding.UTF8, "application/json");

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JObject.Parse(await response.Content.ReadAsStringAsync());
        return json["number"]?.Value<int>() ?? 0;
    }

    public async Task<bool> ValidateTokenAsync(string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Get, "https://api.github.com/user");
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        return response.IsSuccessStatusCode;
    }

    public async Task<string> GetUserNameAsync(string token)
    {
        var request = new HttpRequestMessage(HttpMethod.Get, "https://api.github.com/user");
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("CodeQualityChecker", "1.0"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = JObject.Parse(await response.Content.ReadAsStringAsync());
        return json["login"]?.ToString() ?? "unknown";
    }
}

public class GitFileInfo
{
    public string Name { get; set; } = "";
    public string Path { get; set; } = "";
    public string Type { get; set; } = "file";
    public long Size { get; set; }
    public string? DownloadUrl { get; set; }
}

public class GitCommitResult
{
    public bool Success { get; set; }
    public string? ErrorMessage { get; set; }
    public string? BranchName { get; set; }
    public string? PullRequestUrl { get; set; }
    public int PullRequestNumber { get; set; }
}
