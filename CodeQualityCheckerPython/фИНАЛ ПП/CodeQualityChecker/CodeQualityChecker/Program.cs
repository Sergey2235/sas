var builder = WebApplication.CreateBuilder(args);

// ��������� �������
builder.Services.AddControllers();
builder.Services.AddHttpClient<LlmService>(client =>
{
    client.Timeout = TimeSpan.FromMinutes(20); // ����������� ������� �� 20 �����
});
builder.Services.AddHttpClient<GitHubService>();
builder.Services.AddHttpClient<GitLabService>();

// ������������ ������� �������
builder.Services.AddSingleton<AnalysisHistoryService>();

// ��������� CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll",
        policy => policy.AllowAnyOrigin()
                       .AllowAnyMethod()
                       .AllowAnyHeader());
});

var app = builder.Build();

// ���������� CORS (�� UseRouting!)
app.UseCors("AllowAll");

// ����������� �����
app.UseStaticFiles();

// �������������
app.UseRouting();

// �������� � ����� �� index.html
app.MapGet("/", () => Results.Redirect("/index.html"));

// ���������� API-�����������
app.MapControllers();

app.Run();