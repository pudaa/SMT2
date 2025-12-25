from src.configs.base_config import get_extractor_model
from typing import List
from src.utils.lightweight_tag_extractor import LightweightTagExtractor
from src.configs.base_config import get_color, get_todo_poses

JIEBA_AVAILABLE = get_extractor_model() == 'jieba'

class TodoTagExtractor:
    """
    从待办事项中提取标签的工具类，根据配置选择使用jieba进行中文分词和词性标注，
    或使用轻量级的自定义算法
    """
    
    # jieba加载状态
    _jieba_loaded = False
    
    # 停用词列表
    CHINESE_STOPWORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '还', '把', '又', '来', '对', '但', '从', '给', '到', '等',
        '可以', '要', '需要', '可能', '应该', '想要', '打算', '计划'
    }
    
    ENGLISH_STOPWORDS = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
        'with', 'by', 'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall', 'should',
        'may', 'might', 'must', 'can', 'could', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'my', 'your', 'his', 'her', 'its', 'our', 'their'
    }
    
    @staticmethod
    def extract_tags(text: str) -> List[str]:
        """
        Args:
            text: 待办事项文本
            
        Returns:
            提取出的标签列表
        """
        if not text or not isinstance(text, str):
            return []
        
        # 清理文本
        text = text.strip()
        if not text:
            return []
        
        # 如果jieba可用，使用jieba进行中文分词和词性标注
        if JIEBA_AVAILABLE:
            try:
                return TodoTagExtractor._extract_with_jieba(text)
            except Exception:
                # 如果jieba处理失败，降级到轻量级提取器
                return TodoTagExtractor._extract_with_regex(text)
        else:
            # 否则使用轻量级提取器
            return TodoTagExtractor._extract_with_regex(text)
    
    @staticmethod
    def _extract_with_jieba(text: str) -> List[str]:
        """使用jieba分词提取标签，仅在调用时加载词典"""
        try:
            # 动态导入jieba以减少内存占用
            import jieba.posseg as pseg
            from collections import Counter
            
            # 添加教育技术领域自定义词典（减少对大词典的依赖）
            education_tech_words = [
                '课程开发', '教育应用', '教学设计', '微课', '慕课', '在线课程', '混合学习',
                '翻转课堂', '项目学习', '学习管理系统', 'LMS', 'SCORM', 'xAPI', 'EdTech',
                '教育技术', '数字学习', '智慧教育', '个性化学习', '适应性学习', '学习分析',
                '教学资源', '互动白板', '虚拟现实', '增强现实', '移动学习', '游戏化学习',
                '学习对象', '内容管理系统', '学习路径', '评估系统', '反馈机制', '协作学习',
                '同步教学', '异步教学', '视频会议', '远程教育', '网络课程', '电子教材',
                '学习平台', '教学平台', '教育软件', '学习软件', '教学工具', '学习工具'
            ]
            
            # 仅在首次加载时添加词典
            if not TodoTagExtractor._jieba_loaded:
                import jieba
                for word in education_tech_words:
                    jieba.add_word(word)
                TodoTagExtractor._jieba_loaded = True
            
            # 分词并标注词性
            words = pseg.cut(text)
            
            # 提取名词(n)、英文(eng)等作为标签
            tags = []
            for word, flag in words:
                # 跳过停用词
                if word in TodoTagExtractor.CHINESE_STOPWORDS or word in TodoTagExtractor.ENGLISH_STOPWORDS:
                    continue
                
                # 选择合适的词性或自定义词，转为tuple
                if flag.startswith(tuple(get_todo_poses())) or word in education_tech_words:  # 名词、英文或自定义词
                    if len(word) > 1 or ('\u4e00' <= word <= '\u9fff'):
                        tags.append(word)
            
            
            # 统计词频并按频率排序（降序）
            word_freq = Counter(tags)
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
           
            # 去重并限制标签数量
            unique_tags = []
            seen = set()
            for word, freq in sorted_words:
                if word not in seen:
                    unique_tags.append(word)
                    seen.add(word)
                    if len(unique_tags) >= 10:  # 最多返回10个标签
                        break
            
            return unique_tags
            
        except Exception as e:
            # 如果jieba处理失败，降级到轻量级提取器
            print(f"Jieba extraction failed: {e}")
            return TodoTagExtractor._extract_with_regex(text)
    
    @staticmethod
    def _extract_with_regex(text: str) -> List[str]:
        """使用轻量级提取器提取标签"""
        return LightweightTagExtractor.extract_tags(text, max_tags=10)
