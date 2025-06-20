import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import requests
import json

class AITextDetector:
    """
    A utility class for detecting AI-generated text using multiple open source models.
    """
    
    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the detector."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_model(self, model_name: str = "roberta-base-openai-detector") -> bool:
        """
        Load a specific AI detection model.
        
        Args:
            model_name: Name of the model to load. Options:
                - "roberta-base-openai-detector": OpenAI's RoBERTa detector
                - "roberta-large-openai-detector": OpenAI's RoBERTa large detector
                - "hello-simpleai/chatgpt-detector-roberta": ChatGPT detector
                - "andreas122001/roberta-mixed-detector": Mixed AI detector
                - "AI4Bharat/IndicBERTv2-MLM-only": Good for multilingual detection
                - "microsoft/DialoGPT-medium": Dialog-specific detection
                - "unitary/toxic-bert": Can help identify AI patterns
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            model_map = {
                "roberta-base-openai-detector": "roberta-base-openai-detector",
                "roberta-large-openai-detector": "roberta-large-openai-detector", 
                "chatgpt-detector": "hello-simpleai/chatgpt-detector-roberta",
                "mixed-detector": "andreas122001/roberta-mixed-detector",
                "multilingual-detector": "papluca/xlm-roberta-base-language-detection",
                "distilbert-detector": "distilbert-base-uncased-finetuned-sst-2-english",
                "bert-detector": "textattack/bert-base-uncased-ag-news"
            }
            
            hf_model_name = model_map.get(model_name, model_name)
            
            self.logger.info(f"Loading model: {hf_model_name}")
            
            self.tokenizers[model_name] = AutoTokenizer.from_pretrained(hf_model_name)
            self.models[model_name] = AutoModelForSequenceClassification.from_pretrained(hf_model_name)
            self.models[model_name].to(self.device)
            self.models[model_name].eval()
            
            self.logger.info(f"Successfully loaded model: {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {str(e)}")
            return False
    
    def detect_single_model(self, text: str, model_name: str) -> Dict[str, float]:
        """
        Detect AI-generated text using a single model.
        
        Args:
            text: Input text to analyze
            model_name: Name of the model to use
            
        Returns:
            Dict with 'ai_probability' and 'human_probability'
        """
        if model_name not in self.models:
            if not self.load_model(model_name):
                raise ValueError(f"Failed to load model: {model_name}")
        
        try:
            # Tokenize the input text
            inputs = self.tokenizers[model_name](
                text, 
                return_tensors="pt", 
                truncation=True, 
                padding=True, 
                max_length=512
            ).to(self.device)
            
            # Get model predictions
            with torch.no_grad():
                outputs = self.models[model_name](**inputs)
                probabilities = torch.softmax(outputs.logits, dim=-1)
                
            # Convert to numpy for easier handling
            probs = probabilities.cpu().numpy()[0]
            
            # Most models output [human, ai] probabilities
            if len(probs) == 2:
                human_prob = float(probs[0])
                ai_prob = float(probs[1])
            else:
                # Handle edge cases
                ai_prob = float(probs[0]) if len(probs) == 1 else 0.5
                human_prob = 1.0 - ai_prob
            
            return {
                'ai_probability': ai_prob,
                'human_probability': human_prob,
                'model_used': model_name
            }
            
        except Exception as e:
            self.logger.error(f"Error during detection with {model_name}: {str(e)}")
            return {
                'ai_probability': 0.5,
                'human_probability': 0.5,
                'model_used': model_name,
                'error': str(e)
            }
    
    def detect_ensemble(self, text: str, models: Optional[List[str]] = None) -> Dict:
        """
        Detect AI-generated text using multiple models and ensemble their results.
        
        Args:
            text: Input text to analyze
            models: List of model names to use. If None, uses default models.
            
        Returns:
            Dict with ensemble results and individual model results
        """
        if models is None:
            models = [
                "chatgpt-detector",
                "mixed-detector"
            ]
        
        results = {}
        ai_probs = []
        human_probs = []
        
        for model_name in models:
            try:
                result = self.detect_single_model(text, model_name)
                results[model_name] = result
                
                if 'error' not in result:
                    ai_probs.append(result['ai_probability'])
                    human_probs.append(result['human_probability'])
                    
            except Exception as e:
                self.logger.error(f"Error with model {model_name}: {str(e)}")
                results[model_name] = {
                    'error': str(e),
                    'ai_probability': 0.5,
                    'human_probability': 0.5
                }
        
        # Calculate ensemble results
        if ai_probs:
            ensemble_ai_prob = np.mean(ai_probs)
            ensemble_human_prob = np.mean(human_probs)
            confidence = 1.0 - np.std(ai_probs)  # Higher std = lower confidence
        else:
            ensemble_ai_prob = 0.5
            ensemble_human_prob = 0.5
            confidence = 0.0
        
        ensemble_result = {
            'ensemble_ai_probability': float(ensemble_ai_prob),
            'ensemble_human_probability': float(ensemble_human_prob),
            'confidence': float(max(0.0, confidence)),
            'prediction': 'AI-generated' if ensemble_ai_prob > 0.5 else 'Human-written',
            'individual_results': results,
            'models_used': models
        }
        
        return ensemble_result
    
    def analyze_text_segments(self, text: str, segment_length: int = 200) -> Dict:
        """
        Analyze text by breaking it into segments for more detailed analysis.
        
        Args:
            text: Input text to analyze
            segment_length: Length of each segment in characters
            
        Returns:
            Dict with segment-wise analysis and overall results
        """
        # Split text into segments
        segments = [text[i:i+segment_length] for i in range(0, len(text), segment_length)]
        segment_results = []
        
        for i, segment in enumerate(segments):
            if len(segment.strip()) < 50:  # Skip very short segments
                continue
                
            result = self.detect_ensemble(segment)
            result['segment_index'] = i
            result['segment_text'] = segment[:100] + "..." if len(segment) > 100 else segment
            segment_results.append(result)
        
        # Calculate overall statistics
        if segment_results:
            overall_ai_prob = np.mean([r['ensemble_ai_probability'] for r in segment_results])
            overall_confidence = np.mean([r['confidence'] for r in segment_results])
            
            # Calculate consistency (how similar are the predictions across segments)
            ai_probs = [r['ensemble_ai_probability'] for r in segment_results]
            consistency = 1.0 - np.std(ai_probs) if len(ai_probs) > 1 else 1.0
        else:
            overall_ai_prob = 0.5
            overall_confidence = 0.0
            consistency = 0.0
        
        return {
            'overall_ai_probability': float(overall_ai_prob),
            'overall_prediction': 'AI-generated' if overall_ai_prob > 0.5 else 'Human-written',
            'confidence': float(overall_confidence),
            'consistency': float(max(0.0, consistency)),
            'segment_results': segment_results,
            'total_segments': len(segment_results),
            'text_length': len(text)
        }
    
    def detect_ai_lines(self, text: str, threshold: float = 0.6, min_line_length: int = 20) -> Dict:
        """
        Detect which specific lines in the text are likely AI-generated.
        
        Args:
            text: Input text to analyze
            threshold: Threshold for considering a line AI-generated (0.0 to 1.0)
            min_line_length: Minimum line length to analyze (characters)
            
        Returns:
            Dict with line-by-line analysis results
        """
        lines = text.split('\n')
        line_results = []
        ai_detected_lines = []
        human_lines = []
        
        for i, line in enumerate(lines):
            # Skip empty or very short lines
            if len(line.strip()) < min_line_length:
                continue
            
            try:
                # Analyze each line
                result = self.detect_ensemble(line.strip())
                ai_prob = result['ensemble_ai_probability']
                
                line_analysis = {
                    'line_number': i + 1,
                    'line_text': line.strip(),
                    'ai_probability': ai_prob,
                    'is_ai_generated': ai_prob > threshold,
                    'confidence': result['confidence']
                }
                
                line_results.append(line_analysis)
                
                if ai_prob > threshold:
                    ai_detected_lines.append({
                        'line_number': i + 1,
                        'text': line.strip(),
                        'ai_probability': ai_prob
                    })
                else:
                    human_lines.append({
                        'line_number': i + 1,
                        'text': line.strip(),
                        'ai_probability': ai_prob
                    })
                    
            except Exception as e:
                self.logger.error(f"Error analyzing line {i+1}: {str(e)}")
                continue
        
        # Calculate overall statistics
        if line_results:
            total_lines = len(line_results)
            ai_lines_count = len(ai_detected_lines)
            human_lines_count = len(human_lines)
            
            overall_ai_percentage = (ai_lines_count / total_lines) * 100
            avg_ai_probability = np.mean([r['ai_probability'] for r in line_results])
            
        else:
            total_lines = ai_lines_count = human_lines_count = 0
            overall_ai_percentage = avg_ai_probability = 0.0
        
        return {
            'ai_detected_lines': ai_detected_lines,
            'human_lines': human_lines,
            'line_analysis': line_results,
            'statistics': {
                'total_lines_analyzed': total_lines,
                'ai_generated_lines': ai_lines_count,
                'human_written_lines': human_lines_count,
                'ai_percentage': float(overall_ai_percentage),
                'average_ai_probability': float(avg_ai_probability)
            },
            'threshold_used': threshold
        }

    def detect_ai_sentences(self, text: str, threshold: float = 0.6) -> Dict:
        """
        Detect which specific sentences in the text are likely AI-generated.
        More granular than line detection.
        
        Args:
            text: Input text to analyze
            threshold: Threshold for considering a sentence AI-generated
            
        Returns:
            Dict with sentence-by-sentence analysis results
        """
        import re
        
        # Split text into sentences using regex
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        sentence_results = []
        ai_detected_sentences = []
        human_sentences = []
        
        for i, sentence in enumerate(sentences):
            try:
                result = self.detect_ensemble(sentence)
                ai_prob = result['ensemble_ai_probability']
                
                sentence_analysis = {
                    'sentence_number': i + 1,
                    'sentence_text': sentence,
                    'ai_probability': ai_prob,
                    'is_ai_generated': ai_prob > threshold,
                    'confidence': result['confidence']
                }
                
                sentence_results.append(sentence_analysis)
                
                if ai_prob > threshold:
                    ai_detected_sentences.append({
                        'sentence_number': i + 1,
                        'text': sentence,
                        'ai_probability': ai_prob
                    })
                else:
                    human_sentences.append({
                        'sentence_number': i + 1,
                        'text': sentence,
                        'ai_probability': ai_prob
                    })
                    
            except Exception as e:
                self.logger.error(f"Error analyzing sentence {i+1}: {str(e)}")
                continue
        
        # Calculate statistics
        if sentence_results:
            total_sentences = len(sentence_results)
            ai_sentences_count = len(ai_detected_sentences)
            ai_percentage = (ai_sentences_count / total_sentences) * 100
            avg_ai_probability = np.mean([r['ai_probability'] for r in sentence_results])
        else:
            total_sentences = ai_sentences_count = 0
            ai_percentage = avg_ai_probability = 0.0
        
        return {
            'ai_detected_sentences': ai_detected_sentences,
            'human_sentences': human_sentences,
            'sentence_analysis': sentence_results,
            'statistics': {
                'total_sentences_analyzed': total_sentences,
                'ai_generated_sentences': ai_sentences_count,
                'human_written_sentences': len(human_sentences),
                'ai_percentage': float(ai_percentage),
                'average_ai_probability': float(avg_ai_probability)
            },
            'threshold_used': threshold
        }
    
    def get_available_models(self) -> List[str]:
        """
        Get list of all available AI detection models.
        
        Returns:
            List of available model names
        """
        return [
            "roberta-base-openai-detector",
            "roberta-large-openai-detector",
            "chatgpt-detector",
            "mixed-detector",
            "multilingual-detector",
            "distilbert-detector",
            "bert-detector"
        ]
    
    def load_all_models(self) -> Dict[str, bool]:
        """
        Load all available AI detection models.
        
        Returns:
            Dict with model names and their loading status
        """
        available_models = self.get_available_models()
        loading_results = {}
        
        for model_name in available_models:
            try:
                success = self.load_model(model_name)
                loading_results[model_name] = success
                if success:
                    self.logger.info(f"Successfully loaded {model_name}")
                else:
                    self.logger.warning(f"Failed to load {model_name}")
            except Exception as e:
                self.logger.error(f"Error loading {model_name}: {str(e)}")
                loading_results[model_name] = False
        
        return loading_results
    
    def detect_all_models(self, text: str) -> Dict:
        """
        Detect AI-generated text using ALL available models.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dict with results from all models and ensemble
        """
        available_models = self.get_available_models()
        return self.detect_ensemble(text, models=available_models)
    
    def detect_selected_models(self, text: str, selected_models: List[str]) -> Dict:
        """
        Detect AI-generated text using specific selected models.
        
        Args:
            text: Input text to analyze
            selected_models: List of specific model names to use
            
        Returns:
            Dict with results from selected models and ensemble
        """
        # Validate that selected models are available
        available_models = self.get_available_models()
        valid_models = [model for model in selected_models if model in available_models]
        
        if not valid_models:
            raise ValueError(f"None of the selected models are available. Available models: {available_models}")
        
        if len(valid_models) != len(selected_models):
            invalid_models = [model for model in selected_models if model not in available_models]
            self.logger.warning(f"Invalid models ignored: {invalid_models}")
        
        return self.detect_ensemble(text, models=valid_models)
    
    def detect_top_n_models(self, text: str, n: int = 3, criteria: str = "performance") -> Dict:
        """
        Detect AI-generated text using top N models based on specified criteria.
        
        Args:
            text: Input text to analyze
            n: Number of top models to use
            criteria: Selection criteria ('performance', 'speed', 'accuracy')
            
        Returns:
            Dict with results from top N models and ensemble
        """
        # Define model rankings based on different criteria
        model_rankings = {
            "performance": [
                "mixed-detector",
                "roberta-large-openai-detector", 
                "chatgpt-detector",
                "roberta-base-openai-detector",
                "multilingual-detector",
                "distilbert-detector",
                "bert-detector"
            ],
            "speed": [
                "roberta-base-openai-detector",
                "distilbert-detector",
                "chatgpt-detector",
                "mixed-detector",
                "roberta-large-openai-detector",
                "multilingual-detector",
                "bert-detector"
            ],
            "accuracy": [
                "mixed-detector",
                "roberta-large-openai-detector",
                "chatgpt-detector",
                "roberta-base-openai-detector",
                "multilingual-detector",
                "distilbert-detector",
                "bert-detector"
            ]
        }
        
        if criteria not in model_rankings:
            raise ValueError(f"Invalid criteria. Choose from: {list(model_rankings.keys())}")
        
        top_models = model_rankings[criteria][:n]
        
        return self.detect_ensemble(text, models=top_models)

def detect_with_all_models(text: str) -> Dict:
    """
    Convenience function to detect AI text using all available models.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Detection results from all models
    """
    detector = AITextDetector()
    return detector.detect_all_models(text)

def detect_with_selected_models(text: str, models: List[str]) -> Dict:
    """
    Convenience function to detect AI text using specific selected models.
    
    Args:
        text: Input text to analyze
        models: List of specific model names to use
        
    Returns:
        Detection results from selected models
    """
    detector = AITextDetector()
    return detector.detect_selected_models(text, models)

def detect_with_top_models(text: str, n: int = 3, criteria: str = "performance") -> Dict:
    """
    Convenience function to detect AI text using top N models.
    
    Args:
        text: Input text to analyze
        n: Number of top models to use
        criteria: Selection criteria ('performance', 'speed', 'accuracy')
        
    Returns:
        Detection results from top N models
    """
    detector = AITextDetector()
    return detector.detect_top_n_models(text, n, criteria)

def get_available_models() -> List[str]:
    """
    Get list of all available model names.
    
    Returns:
        List of available model names
    """
    detector = AITextDetector()
    return detector.get_available_models()

def get_ai_lines(text: str, threshold: float = 0.6, min_line_length: int = 20) -> List[str]:
    """
    Get just the AI-detected lines from text.
    """
    detector = AITextDetector()
    result = detector.detect_ai_lines(text, threshold, min_line_length)
    return [line['text'] for line in result['ai_detected_lines']]  # Only returns text

def get_ai_sentences(text: str, threshold: float = 0.6) -> List[str]:
    """
    Get just the AI-detected sentences from text.
    
    Args:
        text: Input text to analyze
        threshold: Threshold for considering a sentence AI-generated
        
    Returns:
        List of AI-detected sentence texts
    """
    detector = AITextDetector()
    result = detector.detect_ai_sentences(text, threshold)
    return [sentence['text'] for sentence in result['ai_detected_sentences']]

def highlight_ai_text(text: str, threshold: float = 0.6, output_format: str = "markdown") -> str:
    """
    Highlight AI-detected portions in text with different formatting.
    
    Args:
        text: Input text to analyze
        threshold: Threshold for considering text AI-generated
        output_format: Output format ('markdown', 'html', 'plain')
        
    Returns:
        Text with AI portions highlighted according to format
    """
    detector = AITextDetector()
    result = detector.detect_ai_sentences(text, threshold)
    
    highlighted_text = text
    
    # Sort sentences by position in text (reverse order to avoid index shifting)
    ai_sentences = sorted(result['ai_detected_sentences'], 
                         key=lambda x: text.find(x['text']), reverse=True)
    
    for sentence_info in ai_sentences:
        sentence = sentence_info['text']
        ai_prob = sentence_info['ai_probability']
        
        # Find sentence in original text
        start_pos = highlighted_text.find(sentence)
        if start_pos != -1:
            if output_format == "markdown":
                highlighted_sentence = f"**[AI: {ai_prob:.2f}]** {sentence}"
            elif output_format == "html":
                highlighted_sentence = f'<span style="background-color: #ffcccc; font-weight: bold;">[AI: {ai_prob:.2f}] {sentence}</span>'
            elif output_format == "plain":
                highlighted_sentence = f"[AI-DETECTED: {ai_prob:.2f}] {sentence}"
            else:
                highlighted_sentence = sentence
            
            highlighted_text = (highlighted_text[:start_pos] + 
                              highlighted_sentence + 
                              highlighted_text[start_pos + len(sentence):])
    
    return highlighted_text

def detect_ai_text(text: str, method: str = "ensemble") -> Dict:
    """
    Detect AI-generated text using specified method.
    
    Args:
        text: Input text to analyze
        method: Detection method ('ensemble', 'all_models', 'fast')
        
    Returns:
        Detection results
    """
    detector = AITextDetector()
    
    if method == "all_models":
        return detector.detect_all_models(text)
    elif method == "fast":
        return detector.detect_ensemble(text, models=["roberta-base-openai-detector"])
    else:  # ensemble (default)
        return detector.detect_ensemble(text)

def is_ai_generated(text: str, threshold: float = 0.7) -> Tuple[bool, float]:
    """
    Simple function to check if text is AI-generated.
    
    Args:
        text: Input text to analyze
        threshold: Threshold for AI detection
        
    Returns:
        Tuple of (is_ai_generated, confidence)
    """
    result = detect_ai_text(text)
    ai_prob = result['ensemble_ai_probability']
    confidence = result['confidence']
    
    return ai_prob > threshold, confidence

# Update the example usage section
if __name__ == "__main__":
    # Example texts for testing
    sample_text = """
    I woke up this morning feeling absolutely terrible. My head was pounding, and I could barely keep my eyes open.
    Artificial intelligence has revolutionized numerous industries by providing automated solutions that enhance efficiency and accuracy.
    The implementation of machine learning algorithms enables systems to learn from data patterns and make informed decisions.
    I think I might be coming down with something, so I decided to stay home today.
    """
    
    print("=== Available Models ===")
    available = get_available_models()
    print(f"Available models: {available}")
    
    print("\n=== Detection with All Models ===")
    all_results = detect_with_all_models(sample_text)
    print(f"Ensemble AI probability: {all_results['ensemble_ai_probability']:.3f}")
    print(f"Models used: {all_results['models_used']}")
    
    print("\n=== Detection with Selected Models ===")
    selected_models = ["chatgpt-detector", "mixed-detector", "guard-detector"]
    selected_results = detect_with_selected_models(sample_text, selected_models)
    print(f"Ensemble AI probability: {selected_results['ensemble_ai_probability']:.3f}")
    print(f"Models used: {selected_results['models_used']}")
    
    print("\n=== Detection with Top 3 Performance Models ===")
    top_results = detect_with_top_models(sample_text, n=3, criteria="performance")
    print(f"Ensemble AI probability: {top_results['ensemble_ai_probability']:.3f}")
    print(f"Models used: {top_results['models_used']}")
    
    print("\n=== AI Line Detection ===")
    ai_lines = get_ai_lines(sample_text)
    print("AI-detected lines:")
    for line in ai_lines:
        print(f"- {line}")
    
    print("\n=== AI Sentence Detection ===")
    ai_sentences = get_ai_sentences(sample_text)
    print("AI-detected sentences:")
    for sentence in ai_sentences:
        print(f"- {sentence}")
    
    print("\n=== Highlighted Text ===")
    highlighted = highlight_ai_text(sample_text, output_format="markdown")
    print(highlighted)

def get_ai_lines_with_details(text: str, threshold: float = 0.6, min_line_length: int = 20) -> List[Dict]:
    """
    Get AI-detected lines with full details including line numbers and probabilities.
    
    Args:
        text: Input text to analyze
        threshold: Threshold for considering a line AI-generated
        min_line_length: Minimum line length to analyze
        
    Returns:
        List of dictionaries with line details
    """
    detector = AITextDetector()
    result = detector.detect_ai_lines(text, threshold, min_line_length)
    return result['ai_detected_lines']

def get_ai_lines_formatted(text: str, threshold: float = 0.6, min_line_length: int = 20) -> str:
    """
    Get AI-detected lines formatted as a readable string.
    
    Args:
        text: Input text to analyze
        threshold: Threshold for considering a line AI-generated
        min_line_length: Minimum line length to analyze
        
    Returns:
        Formatted string with AI lines and their details
    """
    detector = AITextDetector()
    result = detector.detect_ai_lines(text, threshold, min_line_length)
    
    formatted_lines = []
    for line in result['ai_detected_lines']:
        formatted_lines.append(f"Line {line['line_number']} (AI: {line['ai_probability']:.2f}): {line['text']}")
    
    return '\n'.join(formatted_lines)