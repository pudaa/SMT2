import re
from typing import List
from collections import Counter

class LightweightTagExtractor:
    # 简化的停用词列表
    STOPWORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '还', '把', '又', '来', '对', '但', '从', '给', '等',
        '可以', '需要', '可能', '应该', '想要', '打算', '计划', '完成', '进行', '与'
    }
    
    @staticmethod
    def extract_hashtag_tags(text: str) -> List[str]:
        """
        提取文本中的#标签格式关键词
        例如：#课程开发 #教育应用
        """
        # 使用正则表达式匹配[]包围的标签，允许中文、英文、数字、下划线
        hashtag_pattern = r'\[([\u4e00-\u9fff\w]+)\]'
        matches = re.findall(hashtag_pattern, text)
        # 过滤掉太短的标签（少于2个字符）
        return [tag for tag in matches if len(tag) >= 2]
    
    @staticmethod
    def extract_tags(text: str, max_tags: int = 10) -> List[str]:
        """
        简化的标签提取：基于词频统计
        """
        # 预处理：清理文本
        text = text.strip()
        if not text:
            return []
        
        # 步骤1：提取中括号标签（优先级最高）
        hashtag_tags = LightweightTagExtractor.extract_hashtag_tags(text)
        if len(hashtag_tags) >= max_tags:
            return hashtag_tags[:max_tags]
        
        # 步骤2：用正则表达式提取所有候选词
        # 中文词（连续的2-4个字符）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        # 英文单词（2个字符以上）
        english_words = re.findall(r'[a-zA-Z]{2,}', text)
        
        all_words = chinese_words + english_words
        
        # 步骤3：过滤停用词
        filtered_words = []
        for word in all_words:
            word_lower = word.lower()
            # 同时检查word中是否包含停用词
            if (word not in LightweightTagExtractor.STOPWORDS and 
                word_lower not in LightweightTagExtractor.STOPWORDS and
                not any(stopword in word for stopword in LightweightTagExtractor.STOPWORDS)
                ):
                filtered_words.append(word)
        
        # 步骤4：统计词频
        if not filtered_words:
            return hashtag_tags
        
        word_freq = Counter(filtered_words)
        
        # 步骤5：按频率排序，返回前N个
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # 合并hashtag标签和频率标签
        result_tags = hashtag_tags.copy()
        seen = set(hashtag_tags)
        
        for word, freq in sorted_words:
            if word not in seen:
                result_tags.append(word)
                seen.add(word)
                if len(result_tags) >= max_tags:
                    break
        
        return result_tags