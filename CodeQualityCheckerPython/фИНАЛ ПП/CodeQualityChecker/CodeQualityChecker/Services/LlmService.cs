using System.Net.Http.Headers;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

public class LlmService
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _config;

    public LlmService(HttpClient httpClient, IConfiguration config)
    {
        _httpClient = httpClient;
        _config = config;
        _httpClient.BaseAddress = new Uri(_config["LlmSettings:BaseUrl"]);
        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", _config["LlmSettings:ApiKey"]);
    }

    public async Task<string> AnalyzeCodeAsync(CodeSubmission submission, AnalysisType analysisType)
    {
        var prompt = GeneratePrompt(submission.Code, submission.Language, analysisType);

        var requestData = new
        {
            model = _config["LlmSettings:ModelName"],
            messages = new[]
            {
                new { role = "system", content = GetSystemPrompt(submission.Language, analysisType) },
                new { role = "user", content = prompt }
            },
            temperature = GetTemperature(analysisType),
            max_tokens = submission.ComplexityLimit > 500 ? 4000 : 2000
        };

        string responseContent = null;

        try
        {
            var response = await _httpClient.PostAsJsonAsync("/v1/chat/completions", requestData);
            response.EnsureSuccessStatusCode();

            responseContent = await response.Content.ReadAsStringAsync();
            Console.WriteLine($"Raw response from LM Studio: {responseContent}");

            // Парсим весь ответ как JObject
            var json = JObject.Parse(responseContent);

            // Получаем содержимое сообщения
            var contentToken = json["choices"]?[0]?["message"]?["content"];

            if (contentToken == null)
            {
                return $"❌ Модель не вернула содержимое. Raw: {responseContent}";
            }

            var content = contentToken.ToString();

            // Ищем JSON-блок между ```json и ```
            var jsonStart = content.IndexOf("```json");
            var jsonEnd = content.LastIndexOf("```");

            if (jsonStart >= 0 && jsonEnd > jsonStart)
            {
                var jsonText = content.Substring(jsonStart + 7, jsonEnd - jsonStart - 7).Trim();
                return jsonText; // Возвращаем только JSON
            }

            // Если JSON-блок не найден, пробуем парсить весь ответ
            try
            {
                JToken.Parse(content); // Попытка парсинга
                return content; // Если успешно — возвращаем как есть
            }
            catch
            {
                return $"⚠️ Ответ модели не является JSON. Содержимое: {content}";
            }
        }
        catch (Exception ex)
        {
            return $"❌ Ошибка при обращении к модели: {ex.Message}. Raw: {responseContent}";
        }
    }

    private string GetSystemPrompt(string language, AnalysisType analysisType)
    {
        var basePrompt = $"Ты — эксперт по анализу кода на {language}. ";

        switch (analysisType)
        {
            case AnalysisType.SecurityOnly:
                return basePrompt + "Фокусируйся только на безопасности: SQL-инъекции, XSS, утечки данных и другие риски. Не обращай внимания на стиль кода.";

            case AnalysisType.StyleOnly:
                return basePrompt + "Фокусируйся только на стиле: соглашения об именовании, форматирование, читаемость. Не уделяй внимание функциональным ошибкам.";

            case AnalysisType.Performance:
                return basePrompt + "Фокусируйся на производительности: эффективность алгоритмов, использование памяти, оптимизация запросов. Предлагай конкретные улучшения для повышения производительности.";

            case AnalysisType.BestPractices:
                return basePrompt + "Фокусируйся на лучших практиках: принципы SOLID, паттерны проектирования, обработка ошибок, тестируемость кода.";

            case AnalysisType.CodeExamples:
                return basePrompt + "Фокусируйся на предоставлении конкретных примеров улучшенного кода. Для каждой проблемы в исходном коде — покажи, как её можно исправить.";

            default:
                return basePrompt + "Всегда отвечай в JSON-формате с детальным анализом по всем аспектам.";
        }
    }

    private string GeneratePrompt(string code, string language, AnalysisType analysisType)
    {
        var basePrompt = $@"Проанализируй следующий {language} код:
{code}

";

        switch (analysisType)
        {
            case AnalysisType.SecurityOnly:
                basePrompt += @"
Верни ответ в формате JSON с единственным свойством:
- 'security_risks': массив строк с описанием уязвимостей безопасности (SQL-инъекции, XSS, утечки данных и т.д.)

Если уязвимостей нет, верни пустой массив.
";
                break;

            case AnalysisType.StyleOnly:
                basePrompt += @"
Верни ответ в формате JSON с единственным свойством:
- 'style_issues': массив строк с нарушениями стиля кода (соглашения об именовании, форматирование, читаемость)

Если нарушений стиля нет, верни ['Стиль кода соответствует стандартам'].
";
                break;

            case AnalysisType.Performance:
                basePrompt += @"
Верни ответ в формате JSON со свойствами:
- 'performance_issues': массив строк с проблемами производительности
- 'optimization_tips': массив строк с предложениями по оптимизации
- 'complexity_score': число от 0 до 10, где 0 - очень низкая производительность, 10 - оптимальная
";
                break;

            case AnalysisType.CodeExamples:
                basePrompt += @"
Верни ответ в формате JSON со свойствами:
- 'code_suggestions': массив строк с примерами улучшенного кода в формате:
  '// Было:\\n[старый код]\\n// Стало:\\n[улучшенный код]'
- 'improvement_reasons': массив строк с объяснением, почему улучшенный код лучше
";
                break;

            case AnalysisType.BestPractices:
                basePrompt += @"
Верни ответ в формате JSON со свойствами:
- 'best_practices': массив строк с несоответствиями лучшим практикам
- 'architecture_issues': массив строк с проблемами архитектуры
- 'improvement_suggestions': массив строк с предложениями по улучшению
";
                break;

            default:
                basePrompt += @"
Верни ответ в формате JSON со свойствами:
- 'errors': массив строк с описанием ошибок,
- 'style_issues': массив строк с нарушениями стиля,
- 'security_risks': массив строк с уязвимостями,
- 'best_practices': массив строк с рекомендациями по лучшим практикам,
- 'performance_issues': массив строк с проблемами производительности,
- 'code_suggestions': массив строк с примерами улучшенного кода (если 'include_code_examples': true),
- 'summary': краткое резюме,
- 'complexity_score': число от 0 до 10 (уровень сложности/читаемости),
- 'maintainability_score': число от 0 до 10 (уровень сопровождаемости),
- 'security_score': число от 0 до 10 (уровень безопасности),
- 'performance_score': число от 0 до 10 (уровень производительности).

Пример ответа:
{
  ""errors"": [""Нет ошибок""],
  ""style_issues"": [""Можно улучшить именование переменных""],
  ""security_risks"": [""Нет уязвимостей""],
  ""best_practices"": [""Используйте константы для магических чисел""],
  ""performance_issues"": [],
  ""code_suggestions"": [
    ""// Было:\\nvar x = 42;\\n// Стало:\\nconst int magicNumber = 42;\\nvar x = magicNumber;""
  ],
  ""summary"": ""Код корректен и соответствует стилю"",
  ""complexity_score"": 7,
  ""maintainability_score"": 8,
  ""security_score"": 10,
  ""performance_score"": 9
}
";
                break;
        }

        // Добавляем контекст для конкретного языка, чтобы анализ был точнее
        switch (language)
        {
            case "Python":
                basePrompt += @"
Для Python: удели особое внимание:
- использованию `if __name__ == '__main__':`
- PEP 8 стилю (именование, отступы)
- безопасности (использование `pickle`, `eval`, `exec`)
- производительности (использование `list comprehensions`, `map`, `filter`).
";
                break;

            case "JavaScript":
                basePrompt += @"
Для JavaScript: удели особое внимание:
- безопасности (XSS, использование `eval`, `innerHTML`)
- стилю (ESLint, соглашения об именовании)
- асинхронности (`async/await`, `Promise`)
- утечкам памяти (замыкания, обработчики событий).
";
                break;

            case "Java":
                basePrompt += @"
Для Java: удели особое внимание:
- соблюдению принципов SOLID
- безопасности (SQL-инъекции, XSS)
- стилю (Google Java Style Guide)
- управлению памятью (утечки, `finalize`)
- производительности (использование `StringBuilder`, `Stream API`).
";
                break;

            case "C#":
                basePrompt += @"
Для C#: удели особое внимание:
- соблюдению .NET Framework Design Guidelines
- безопасности (XSS, SQL-инъекции, утечки памяти)
- стилю (именование, форматирование)
- использованию `async/await`, `LINQ`, `nullable reference types`.
";
                break;

            case "Go":
                basePrompt += @"
Для Go: удели особое внимание:
- соблюдению `gofmt`, `golint`, `go vet`
- безопасности (SQL-инъекции, XSS)
- производительности (использование `goroutines`, `channels`)
- стилю (идиоматичный Go).
";
                break;

            case "Rust":
                basePrompt += @"
Для Rust: удели особое внимание:
- безопасности (владение, заимствование)
- стилю (использование `clippy`, `rustfmt`)
- производительности (использование итераторов, `async`)
- использованию `unsafe`.
";
                break;

            case "PHP":
                basePrompt += @"
Для PHP: удели особое внимание:
- безопасности (SQL-инъекции, XSS, `eval`)
- стилю (PSR-12)
- производительности (кеширование, `opcache`)
- использованию `mysqli`, `PDO`.
";
                break;

            case "Ruby":
                basePrompt += @"
Для Ruby: удели особое внимание:
- стилю (Ruby Style Guide)
- безопасности (SQL-инъекции, XSS)
- использованию `Rails` best practices
- идиоматичности кода.
";
                break;

            case "Swift":
                basePrompt += @"
Для Swift: удели особое внимание:
- безопасности (ARC, утечки памяти)
- стилю (Swift API Design Guidelines)
- использованию `Optionals`, `Closures`, `Protocol-Oriented Programming`.
";
                break;

            case "Kotlin":
                basePrompt += @"
Для Kotlin: удели особое внимание:
- соблюдению Kotlin Coding Conventions
- безопасности (SQL-инъекции, XSS)
- использованию `coroutines`, `null safety`, `extension functions`.
";
                break;

            case "SQL":
                basePrompt += @"
Для SQL: удели особое внимание:
- безопасности (SQL-инъекции, использование `prepared statements`)
- производительности (индексы, `EXPLAIN`, `JOIN`)
- стилю (именование, форматирование).
";
                break;

            case "C++":
                basePrompt += @"
Для C++: удели особое внимание:
- безопасности (`buffer overflow`, `dangling pointers`, RAII)
- стилю (Google C++ Style Guide)
- использованию `STL`, `RAII`, `move semantics`, `templates`
- производительности (`memory allocation`, `cache misses`).
";
                break;

            case "TypeScript":
                basePrompt += @"
Для TypeScript: удели особое внимание:
- использованию `strict mode`, `strictNullChecks`, `strictFunctionTypes`
- типизации (`any`, `unknown`, `never`, `union types`, `generics`)
- безопасности (XSS через React bindings)
- стилю (`TSLint`, `ESLint`, `Prettier`, соглашения об именовании).
";
                break;

            case "C":
                basePrompt += @"
Для C: удели особое внимание:
- безопасности (`buffer overflow`, `unsafe functions`, `scanf`, `gets`)
- стилю (именование, форматирование)
- управлению памятью (утечки, `malloc/free`)
- использованию `const`, `static`, `restrict`.
";
                break;

            case "Objective-C":
                basePrompt += @"
Для Objective-C: удели особое внимание:
- безопасности (ARC, утечки памяти)
- стилю (Apple Coding Guidelines)
- использованию `Blocks`, `Categories`, `Protocols`.
";
                break;
        }

        return basePrompt;
    }

    private double GetTemperature(AnalysisType analysisType)
    {
        switch (analysisType)
        {
            case AnalysisType.SecurityOnly:
                return 0.1; // Минимальная креативность для безопасности
            case AnalysisType.Performance:
                return 0.3; // Средняя креативность для предложений по оптимизации
            case AnalysisType.CodeExamples:
                return 0.4; // Более высокая креативность для генерации примеров
            default:
                return 0.2; // Стандартная температура
        }
    }
}