using Microsoft.Data.Sqlite;
using Newtonsoft.Json;

public class AnalysisHistoryService
{
    private readonly string _dbPath = Path.Combine(AppContext.BaseDirectory, "analysis_history.db");

    public AnalysisHistoryService()
    {
        InitializeDatabase();
    }

    private void InitializeDatabase()
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        connection.Open();

        var createTable = new SqliteCommand(@"
            CREATE TABLE IF NOT EXISTS AnalysisHistory (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                Code TEXT,
                Language TEXT,
                Result TEXT,
                AnalysisType TEXT,
                UserId TEXT DEFAULT 'anonymous'
            )", connection);
        createTable.ExecuteNonQuery();
    }

    public async Task SaveAnalysisAsync(string code, string language, string result, string userId = "default")
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        var insert = new SqliteCommand(@"
            INSERT INTO AnalysisHistory (Code, Language, Result, UserId) 
            VALUES (@code, @language, @result, @userId)", connection);

        insert.Parameters.AddWithValue("@code", code);
        insert.Parameters.AddWithValue("@language", language);
        insert.Parameters.AddWithValue("@result", result);
        insert.Parameters.AddWithValue("@userId", userId);

        await insert.ExecuteNonQueryAsync();
    }

    public async Task<List<AnalysisHistoryItem>> GetHistoryAsync(string userId = "default", int limit = 20)
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        var select = new SqliteCommand(@"
            SELECT Id, Timestamp, Code, Language, Result, AnalysisType 
            FROM AnalysisHistory 
            WHERE UserId = @userId 
            ORDER BY Timestamp DESC 
            LIMIT @limit", connection);

        select.Parameters.AddWithValue("@userId", userId);
        select.Parameters.AddWithValue("@limit", limit);

        using var reader = await select.ExecuteReaderAsync();
        var history = new List<AnalysisHistoryItem>();

        while (await reader.ReadAsync())
        {
            history.Add(new AnalysisHistoryItem
            {
                Id = reader.GetInt32(0),
                Timestamp = reader.GetDateTime(1),
                Code = reader.GetString(2),
                Language = reader.GetString(3),
                Result = reader.GetString(4),
                AnalysisType = reader.GetString(5)
            });
        }

        return history;
    }
}

public class AnalysisHistoryItem
{
    public int Id { get; set; }
    public DateTime Timestamp { get; set; }
    public string Code { get; set; }
    public string Language { get; set; }
    public string Result { get; set; }
    public string AnalysisType { get; set; }
}