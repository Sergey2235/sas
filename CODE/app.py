import os
import requests
import json
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)

# Конфигурация
class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8523664920:AAENFx004lsLW_8Sgffenwu75-GE1xiKmE8')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')    
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    MAX_FILE_SIZE = 1024 * 1024  # 1MB

# Имитация LLM анализа
class CodeAnalyzer:
    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
    
    def analyze_code(self, code: str, language: str) -> dict:
        """Анализ кода с помощью LLM"""
        
        # Если есть реальный API ключ, используем его
        if self.api_key and self.api_key != 'your_openai_api_key_here':
            return self._analyze_with_openai(code, language)
        else:
            # Имитация анализа
            return self._mock_analysis(code, language)
    
    def _analyze_with_openai(self, code: str, language: str) -> dict:
        """Реальный анализ через OpenAI API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            prompt = f"""
            Проанализируй код на {language} и оцени его качество по следующим критериям:
            1. Стиль кода и читаемость
            2. Эффективность алгоритмов
            3. Безопасность
            4. Соответствие best practices
            5. Потенциальные ошибки
            
            Код:
            {code}
            
            Ответь в формате JSON:
            {{
                "score": 0-100,
                "issues": [
                    {{"type": "error/warning/info", "message": "описание", "line": number}}
                ],
                "recommendations": ["рекомендация1", "рекомендация2"],
                "complexity": "low/medium/high"
            }}
            """
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result['choices'][0]['message']['content']
                return json.loads(analysis_text)
            else:
                return self._mock_analysis(code, language)
                
        except Exception as e:
            print(f"OpenAI error: {e}")
            return self._mock_analysis(code, language)
    
    def _mock_analysis(self, code: str, language: str) -> dict:
        """Имитация анализа для демонстрации"""
        lines = code.split('\n')
        issues = []
        
        # Простая эвристика для демонстрации
        if len(code) > 500:
            issues.append({
                "type": "warning",
                "message": "Код слишком длинный, рассмотрите разбиение на функции",
                "line": 1
            })
        
        if 'password' in code.lower() and 'encrypt' not in code.lower():
            issues.append({
                "type": "error", 
                "message": "Обнаружены пароли в открытом виде",
                "line": 0
            })
        
        if 'TODO' in code or 'FIXME' in code:
            issues.append({
                "type": "warning",
                "message": "Обнаружены незавершенные участки кода (TODO/FIXME)",
                "line": 0
            })
        
        if len(lines) > 50:
            issues.append({
                "type": "warning",
                "message": "Функция слишком сложная",
                "line": len(lines)
            })
        
        # Проверка на длинные строки
        for i, line in enumerate(lines):
            if len(line) > 100:
                issues.append({
                    "type": "warning",
                    "message": "Слишком длинная строка кода",
                    "line": i + 1
                })
        
        score = max(0, 100 - len(issues) * 10)
        
        return {
            "score": score,
            "issues": issues,
            "recommendations": [
                "Добавьте комментарии к сложным функциям",
                "Используйте осмысленные имена переменных",
                "Разбейте большие функции на smaller",
                "Удалите неиспользуемый код",
                "Добавьте обработку ошибок"
            ],
            "complexity": "high" if len(lines) > 30 else "medium" if len(lines) > 15 else "low"
        }

# Инициализация анализатора
analyzer = CodeAnalyzer()

@app.route('/')
def index():
    """Главная страница Web App"""
    return render_template('index.html')

@app.route('/webapp')
def webapp():
    """Специальный маршрут для Telegram Web App"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_code():
    """API для анализа кода"""
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        if not code:
            return jsonify({'error': 'Пустой код'}), 400
        
        if len(code) > Config.MAX_FILE_SIZE:
            return jsonify({'error': 'Файл слишком большой'}), 400
        
        # Анализ кода
        analysis_result = analyzer.analyze_code(code, language)
        
        return jsonify({
            'success': True,
            'analysis': analysis_result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Проверка здоровья приложения"""
    return jsonify({'status': 'healthy'})

@app.route('/test')
def test():
    """Тестовая страница"""
    return jsonify({'message': 'Flask app is working!'})

if __name__ == '__main__':
    print("🚀 Запуск Flask приложения...")
    print(f"📊 TELEGRAM_BOT_TOKEN: {'✅' if Config.TELEGRAM_BOT_TOKEN else '❌'}")
    print(f"🤖 OPENAI_API_KEY: {'✅' if Config.OPENAI_API_KEY else '❌'}")
    app.run(host='0.0.0.0', port=5000, debug=True)