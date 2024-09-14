from database import get_training_data, add_pending_data
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def train_model():
    data = get_training_data()
    if not data:
        return None, None, None

    questions = [row[0] for row in data]
    answers = [row[1] for row in data]

    # 使用 TfidfVectorizer 并允许使用双字母词缀作为特征
    vectorizer = TfidfVectorizer(ngram_range=(1, 5), analyzer='char_wb').fit(questions)
    X = vectorizer.transform(questions)

    return vectorizer, X, answers

def find_best_answer(user_question, vectorizer, X, answers):
    user_vec = vectorizer.transform([user_question])
    similarities = cosine_similarity(user_vec, X).flatten()
    best_match_idx = similarities.argmax()

    # 你可以尝试设置一个较低的相似度阈值
    if similarities[best_match_idx] > 0.5:
        return answers[best_match_idx]
    else:
        add_pending_data(user_question)  # 记录未识别问题
        return None



def get_answer_from_training_data(user_question):
    vectorizer, X, answers = train_model()
    
    if vectorizer is not None:
        return find_best_answer(user_question, vectorizer, X, answers)
    
    return None
