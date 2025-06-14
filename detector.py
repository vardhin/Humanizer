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
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            model_map = {
                "roberta-base-openai-detector": "roberta-base-openai-detector",
                "roberta-large-openai-detector": "roberta-large-openai-detector", 
                "chatgpt-detector": "hello-simpleai/chatgpt-detector-roberta",
                "mixed-detector": "andreas122001/roberta-mixed-detector"
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


def detect_ai_text(text: str, method: str = "ensemble", models: Optional[List[str]] = None) -> Dict:
    """
    Convenience function to detect AI-generated text.
    
    Args:
        text: Input text to analyze
        method: Detection method ('single', 'ensemble', 'segments')
        models: List of models to use (for ensemble method)
        
    Returns:
        Detection results as a dictionary
    """
    detector = AITextDetector()
    
    if method == "single":
        model_name = models[0] if models else "chatgpt-detector"
        return detector.detect_single_model(text, model_name)
    elif method == "ensemble":
        return detector.detect_ensemble(text, models)
    elif method == "segments":
        return detector.analyze_text_segments(text)
    else:
        raise ValueError(f"Unknown method: {method}")


def is_ai_generated(text: str, threshold: float = 0.7) -> Tuple[bool, float]:
    """
    Simple function to check if text is AI-generated.
    
    Args:
        text: Input text to analyze
        threshold: Threshold for AI detection (0.0 to 1.0)
        
    Returns:
        Tuple of (is_ai_generated: bool, confidence: float)
    """
    result = detect_ai_text(text, method="ensemble")
    ai_prob = result['ensemble_ai_probability']
    is_ai = ai_prob > threshold
    
    return is_ai, ai_prob


# Example usage and testing
if __name__ == "__main__":
    # Example texts for testing
    sample_texts = [
        # Likely human-written
        "I woke up this morning feeling absolutely terrible. My head was pounding, and I could barely keep my eyes open. I think I might be coming down with something.",
        
        # Potentially AI-generated (more formal/structured)
        "Artificial intelligence has revolutionized numerous industries by providing automated solutions that enhance efficiency and accuracy. The implementation of machine learning algorithms enables systems to learn from data patterns and make informed decisions without explicit programming."
    ]
    
    detector = AITextDetector()
    
    for i, text in enumerate(sample_texts):
        print(f"\n--- Analysis for Text {i+1} ---")
        print(f"Text: {text[:100]}...")
        
        # Simple detection
        is_ai, confidence = is_ai_generated(text)
        print(f"Is AI-generated: {is_ai} (confidence: {confidence:.3f})")
        
        # Detailed ensemble analysis
        result = detect_ai_text(text, method="ensemble")
        print(f"Ensemble prediction: {result['prediction']}")
        print(f"AI probability: {result['ensemble_ai_probability']:.3f}")
        print(f"Confidence: {result['confidence']:.3f}")