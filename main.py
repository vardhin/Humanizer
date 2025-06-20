import os
import json
import time
from typing import Dict, Tuple
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import re

# Import our utility modules
from paraphraser import paraphrase_text, load_model, get_available_models, get_current_model, get_device_info
from rewriter import rewrite_text, get_synonym, refine_text
from detector import (
    AITextDetector, 
    detect_with_all_models, 
    detect_with_selected_models, 
    detect_with_top_models,
    get_available_models as get_detection_models,
    get_ai_lines,
    get_ai_sentences,
    highlight_ai_text
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

def clean_final_text(text: str) -> str:
    """
    Clean the final text by:
    1. Replacing every "—" with ", "
    2. Removing spaces that appear before "," or "."
    """
    if not text:
        return text
    
    # Step 1: Replace em dashes with commas
    cleaned_text = text.replace("—", ", ")
    
    # Step 2: Remove spaces before commas and periods
    # This regex finds spaces that are followed by comma or period
    cleaned_text = re.sub(r' +([,.])', r'\1', cleaned_text)
    
    return cleaned_text

class HumanizerService:
    """Main orchestrator service that combines paraphrasing and rewriting"""
    
    def __init__(self):
        logger.info("HumanizerService initialized")
    
    def humanize_text(
        self, 
        text: str, 
        use_paraphrasing: bool = True,
        use_enhanced_rewriting: bool = False,
        paraphrase_model: str = None
    ) -> Tuple[str, Dict]:
        """
        Complete text humanization pipeline:
        1. Paraphrase the text (optional)
        2. Rewrite and refine the result
        3. Clean the final text
        """
        
        stats = {
            "original_length": len(text),
            "paraphrasing_used": False,
            "enhanced_rewriting_used": use_enhanced_rewriting,
            "model_used": None,
            "processing_steps": []
        }
        
        try:
            current_text = text
            
            # Step 1: Paraphrasing (if enabled)
            if use_paraphrasing:
                logger.info("Starting paraphrasing step")
                paraphrased, err = paraphrase_text(current_text, paraphrase_model)
                
                if not err and paraphrased and paraphrased.strip():
                    current_text = paraphrased
                    stats["paraphrasing_used"] = True
                    stats["model_used"] = get_current_model()
                    stats["processing_steps"].append("paraphrasing")
                    logger.info("Paraphrasing successful")
                    
                    # Clean up common formatting issues from paraphrasing
                    if current_text.startswith(": "):
                        current_text = current_text[2:]
                else:
                    logger.warning(f"Paraphrasing failed or skipped: {err}")
                    stats["processing_steps"].append("paraphrasing_failed")
            
            # Step 2: Rewriting and refinement
            logger.info("Starting rewriting step")
            final_text, err = rewrite_text(current_text, enhanced=use_enhanced_rewriting)
            
            if err:
                logger.warning(f"Rewriting failed: {err}")
                final_text = current_text
                stats["processing_steps"].append("rewriting_failed")
            else:
                stats["processing_steps"].append("rewriting")
            
            # Step 3: Clean the final text
            logger.info("Cleaning final text")
            final_text = clean_final_text(final_text)
            stats["processing_steps"].append("text_cleaning")
            
            stats["final_length"] = len(final_text)
            stats["length_change"] = stats["final_length"] - stats["original_length"]
            
            return final_text, stats
            
        except Exception as e:
            logger.error(f"Error in humanization pipeline: {str(e)}")
            return text, {
                **stats,
                "error": str(e),
                "processing_steps": stats["processing_steps"] + ["error"]
            }

# Initialize services
humanizer_service = HumanizerService()
ai_detector = AITextDetector()

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    current_model = get_current_model()
    return jsonify({
        "status": "healthy",
        "message": "🚀 Humanize AI Server is running!",
        "features": {
            "paraphrasing": current_model is not None,
            "current_model": current_model,
            "available_models": get_available_models(),
            "local_refinement": True,
            "synonym_support": True,
            "device": get_device_info()
        }
    })

@app.route('/health', methods=['GET'])
def detailed_health():
    """Detailed health check with system information - matches frontend expectations"""
    current_model = get_current_model()
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "features": {
            "paraphrasing_available": current_model is not None,
            "current_paraphrase_model": current_model,
            "local_processing": True,
            "device": get_device_info()
        },
        "version": "3.0.0"
    })

@app.route('/models', methods=['GET'])
def get_models():
    """Get available paraphrasing models - matches frontend expectations"""
    return jsonify({
        "available_models": get_available_models(),
        "current_model": get_current_model(),
        "device": get_device_info()
    })

@app.route('/load_model', methods=['POST'])
def load_model_endpoint():
    """Load a specific paraphrasing model - matches frontend expectations"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        model_name = data.get('model_name', '').strip()
        
        if not model_name:
            return jsonify({"error": "No model_name provided"}), 400
        
        available_models = get_available_models()
        if model_name not in available_models:
            return jsonify({
                "error": f"Model {model_name} not supported",
                "available_models": available_models
            }), 400
        
        success, error = load_model(model_name)
        if success:
            return jsonify({
                "message": f"Successfully loaded {model_name}",
                "current_model": get_current_model(),
                "success": True
            })
        else:
            return jsonify({"error": error or f"Failed to load model {model_name}"}), 500
        
    except Exception as e:
        logger.error(f"Error in /load_model: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/humanize', methods=['POST'])
def humanize_handler():
    """Main endpoint for humanizing AI-generated text - matches frontend expectations"""
    try:
        logger.info("Humanize request received")
        
        # Validate request
        if not request.is_json:
            logger.error("Invalid content type")
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        if not data or "text" not in data:
            logger.error("Missing text field in request")
            return jsonify({"error": "Text field is required"}), 400
        
        text = data.get("text", "").strip()
        if not text:
            logger.error("Empty text received")
            return jsonify({"error": "Text cannot be empty"}), 400
        
        # Validate text length
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        # Extract options - match frontend parameter names
        use_paraphrasing = data.get("paraphrasing", True)
        use_enhanced = data.get("enhanced", True)  # Changed from False to True
        paraphrase_model = data.get("model", None)
        
        # Process text through humanization pipeline
        humanized_text, stats = humanizer_service.humanize_text(
            text=text,
            use_paraphrasing=use_paraphrasing,
            use_enhanced_rewriting=use_enhanced,  # This will now use the more aggressive mode
            paraphrase_model=paraphrase_model
        )
        
        # Ensure we return something
        if not humanized_text or not humanized_text.strip():
            humanized_text = text
        
        response = {
            "humanized_text": humanized_text,
            "success": True,
            "statistics": stats
        }
        
        logger.info(f"Successfully processed text: {stats['original_length']} -> {stats['final_length']} chars")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "success": False
        }), 500

# Additional endpoints for direct access
@app.route('/paraphrase', methods=['POST'])
def paraphrase_handler():
    """Direct paraphrasing endpoint"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        model_name = data.get('model_name', None)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        paraphrased_text, error = paraphrase_text(text, model_name)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({
            'paraphrased': paraphrased_text,
            'success': True,
            'model_used': get_current_model(),
            'original_text': text
        })

    except Exception as e:
        logger.error(f"Error in /paraphrase: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/synonym', methods=['POST'])
def synonym_handler():
    """Get synonym for a word"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        word = data.get('word', '').strip()
        
        if not word:
            return jsonify({"error": "No word provided"}), 400
        
        synonym, error = get_synonym(word)
        
        if error:
            return jsonify({"error": error}), 400
        
        return jsonify({
            'synonym': synonym,
            'original_word': word,
            'success': True
        })

    except Exception as e:
        logger.error(f"Error in /synonym: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/refine', methods=['POST'])
def refine_handler():
    """Refine text using NLP tools"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        refined_text, error = refine_text(text)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({
            'refined_text': refined_text,
            'original_text': text,
            'success': True
        })

    except Exception as e:
        logger.error(f"Error in /refine: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/paraphrase_only', methods=['POST'])
def paraphrase_only_handler():
    """Paraphrase text without rewriting - for step-by-step processing"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        model_name = data.get('model', None)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        paraphrased_text, error = paraphrase_text(text, model_name)
        
        if error:
            return jsonify({"error": error}), 500
        
        # Clean up common formatting issues
        if paraphrased_text and paraphrased_text.startswith(": "):
            paraphrased_text = paraphrased_text[2:]
        
        return jsonify({
            'paraphrased_text': paraphrased_text or text,
            'success': True,
            'model_used': get_current_model(),
            'original_text': text,
            'statistics': {
                'original_length': len(text),
                'paraphrased_length': len(paraphrased_text) if paraphrased_text else len(text),
                'length_change': (len(paraphrased_text) if paraphrased_text else len(text)) - len(text),
                'model_used': get_current_model(),
                'paraphrasing_used': True
            }
        })

    except Exception as e:
        logger.error(f"Error in /paraphrase_only: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/rewrite_only', methods=['POST'])
def rewrite_only_handler():
    """Rewrite text without paraphrasing - for step-by-step processing"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        enhanced = data.get('enhanced', False)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        rewritten_text, error = rewrite_text(text, enhanced=enhanced)
        
        if error:
            return jsonify({"error": error}), 500
        
        # Clean the final rewritten text
        rewritten_text = clean_final_text(rewritten_text or text)
        
        return jsonify({
            'rewritten_text': rewritten_text,
            'success': True,
            'original_text': text,
            'statistics': {
                'original_length': len(text),
                'rewritten_length': len(rewritten_text),
                'length_change': len(rewritten_text) - len(text),
                'enhanced_rewriting_used': enhanced,
                'text_cleaning_applied': True
            }
        })

    except Exception as e:
        logger.error(f"Error in /rewrite_only: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/paraphrase_multi', methods=['POST'])
def paraphrase_multi_handler():
    """Paraphrase text through 2 best models in PIPELINE (each model processes previous output)"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        # Define the 2 best models (prioritize specialized paraphrasing models)
        best_models = [
            "humarin/chatgpt_paraphraser_on_T5_base",
            "Vamsi/T5_Paraphrase_Paws"
        ]
        
        # Filter available models
        available_models = get_available_models()
        models_to_use = [model for model in best_models if model in available_models]
        
        # Fallback to first 2 available models if best models aren't available
        if len(models_to_use) < 2:
            models_to_use = available_models[:2]
        
        if not models_to_use:
            return jsonify({"error": "No models available for paraphrasing"}), 500
        
        results = []
        errors = []
        current_text = text  # Start with original text
        
        for i, model_name in enumerate(models_to_use):
            try:
                logger.info(f"Pipeline step {i+1}: Paraphrasing with model {model_name}")
                paraphrased_text, error = paraphrase_text(current_text, model_name)
                
                if error:
                    errors.append(f"Step {i+1} ({model_name}): {error}")
                    # On error, continue with current text (don't break the pipeline)
                    paraphrased_text = current_text
                
                # Clean up common formatting issues
                if paraphrased_text and paraphrased_text.startswith(": "):
                    paraphrased_text = paraphrased_text[2:]
                
                # If paraphrasing failed, use current text
                if not paraphrased_text or not paraphrased_text.strip():
                    paraphrased_text = current_text
                
                results.append({
                    "step": i + 1,
                    "model": model_name,
                    "input_text": current_text,
                    "output_text": paraphrased_text,
                    "input_length": len(current_text),
                    "output_length": len(paraphrased_text),
                    "length_change": len(paraphrased_text) - len(current_text),
                    "success": not error
                })
                
                # Update current_text for next iteration (PIPELINE EFFECT)
                current_text = paraphrased_text
                
            except Exception as e:
                logger.error(f"Error with model {model_name}: {str(e)}")
                errors.append(f"Step {i+1} ({model_name}): {str(e)}")
                # Continue with current text on error
                results.append({
                    "step": i + 1,
                    "model": model_name,
                    "input_text": current_text,
                    "output_text": current_text,  # No change on error
                    "input_length": len(current_text),
                    "output_length": len(current_text),
                    "length_change": 0,
                    "success": False,
                    "error": str(e)
                })
        
        return jsonify({
            "pipeline_results": results,
            "success": True,
            "original_text": text,
            "final_text": current_text,  # Final output after all pipeline steps
            "models_used": [r["model"] for r in results],
            "errors": errors if errors else None,
            "statistics": {
                "pipeline_steps": len(results),
                "successful_steps": len([r for r in results if r.get("success", False)]),
                "failed_steps": len([r for r in results if not r.get("success", False)]),
                "original_length": len(text),
                "final_length": len(current_text),
                "total_length_change": len(current_text) - len(text),
                "pipeline_mode": "sequential"
            }
        })

    except Exception as e:
        logger.error(f"Error in /paraphrase_multi: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/paraphrase_all', methods=['POST'])
def paraphrase_all_handler():
    """Paraphrase text through ALL available models in PIPELINE (each model processes previous output)"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        available_models = get_available_models()
        
        if not available_models:
            return jsonify({"error": "No models available for paraphrasing"}), 500
        
        results = []
        errors = []
        current_text = text  # Start with original text
        processing_time_start = time.time()
        
        for i, model_name in enumerate(available_models):
            model_start_time = time.time()
            try:
                logger.info(f"Pipeline step {i+1}/{len(available_models)}: Paraphrasing with model {model_name}")
                paraphrased_text, error = paraphrase_text(current_text, model_name)
                
                model_time = time.time() - model_start_time
                
                if error:
                    errors.append(f"Step {i+1} ({model_name}): {error}")
                    # On error, continue with current text (don't break the pipeline)
                    paraphrased_text = current_text
                
                # Clean up common formatting issues
                if paraphrased_text and paraphrased_text.startswith(": "):
                    paraphrased_text = paraphrased_text[2:]
                
                # If paraphrasing failed, use current text
                if not paraphrased_text or not paraphrased_text.strip():
                    paraphrased_text = current_text
                
                results.append({
                    "step": i + 1,
                    "model": model_name,
                    "input_text": current_text,
                    "output_text": paraphrased_text,
                    "input_length": len(current_text),
                    "output_length": len(paraphrased_text),
                    "length_change": len(paraphrased_text) - len(current_text),
                    "processing_time": round(model_time, 2),
                    "success": not error
                })
                
                # Update current_text for next iteration (PIPELINE EFFECT)
                current_text = paraphrased_text
                
            except Exception as e:
                model_time = time.time() - model_start_time
                logger.error(f"Error with model {model_name}: {str(e)}")
                errors.append(f"Step {i+1} ({model_name}): {str(e)}")
                
                # Continue with current text on error
                results.append({
                    "step": i + 1,
                    "model": model_name,
                    "input_text": current_text,
                    "output_text": current_text,  # No change on error
                    "input_length": len(current_text),
                    "output_length": len(current_text),
                    "length_change": 0,
                    "processing_time": round(model_time, 2),
                    "success": False,
                    "error": str(e)
                })
        
        total_processing_time = time.time() - processing_time_start
        successful_steps = [r for r in results if r.get("success", False)]
        
        return jsonify({
            "pipeline_results": results,
            "successful_steps": successful_steps,
            "success": len(successful_steps) > 0,
            "original_text": text,
            "final_text": current_text,  # Final output after all pipeline steps
            "models_attempted": available_models,
            "errors": errors if errors else None,
            "statistics": {
                "pipeline_steps": len(results),
                "successful_steps": len(successful_steps),
                "failed_steps": len(results) - len(successful_steps),
                "original_length": len(text),
                "final_length": len(current_text),
                "total_length_change": len(current_text) - len(text),
                "total_processing_time": round(total_processing_time, 2),
                "average_processing_time": round(total_processing_time / len(available_models), 2) if available_models else 0,
                "pipeline_mode": "sequential"
            }
        })

    except Exception as e:
        logger.error(f"Error in /paraphrase_all: {str(e)}")
        return jsonify({"error": str(e)}), 500

# AI detection endpoints
@app.route('/detect', methods=['POST'])
def detect_ai_handler():
    """Main AI detection endpoint using ensemble method with enhanced options"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.7)
        models = data.get('models', None)  # Optional specific models
        use_all_models = data.get('use_all_models', False)  # New option
        top_n = data.get('top_n', None)  # New option for top N models
        criteria = data.get('criteria', 'performance')  # New option for model selection criteria
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 20:
            return jsonify({"error": "Text must be at least 20 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 10000 to 50000
            return jsonify({"error": "Text must be less than 50,000 characters"}), 400
        
        # Get detection results based on options
        if use_all_models:
            result = detect_with_all_models(text)
        elif top_n and isinstance(top_n, int) and top_n > 0:
            result = detect_with_top_models(text, n=top_n, criteria=criteria)
        elif models and isinstance(models, list):
            result = detect_with_selected_models(text, models)
        else:
            # Default ensemble method
            detector = AITextDetector()
            result = detector.detect_ensemble(text, models=models)
        
        # Add simple classification
        is_ai = result['ensemble_ai_probability'] > threshold
        
        response = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_ai_generated": is_ai,
            "ai_probability": result['ensemble_ai_probability'],
            "human_probability": result['ensemble_human_probability'],
            "prediction": result['prediction'],
            "confidence": result['confidence'],
            "threshold_used": threshold,
            "models_used": result['models_used'],
            "individual_results": result['individual_results'],
            "text_length": len(text),
            "detection_method": "all_models" if use_all_models else f"top_{top_n}" if top_n else "selected" if models else "default",
            "success": True
        }
        
        logger.info(f"AI detection completed: {result['prediction']} ({result['ensemble_ai_probability']:.3f})")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in AI detection: {str(e)}")
        return jsonify({
            "error": "Failed to analyze text",
            "success": False
        }), 500

@app.route('/detect_all_models', methods=['POST'])
def detect_all_models_handler():
    """Detect AI text using ALL available models"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.7)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 20:
            return jsonify({"error": "Text must be at least 20 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 10000 to 50000
            return jsonify({"error": "Text must be less than 50,000 characters"}), 400
        
        # Use all available models
        result = detect_with_all_models(text)
        is_ai = result['ensemble_ai_probability'] > threshold
        
        response = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_ai_generated": is_ai,
            "ai_probability": result['ensemble_ai_probability'],
            "human_probability": result['ensemble_human_probability'],
            "prediction": result['prediction'],
            "confidence": result['confidence'],
            "threshold_used": threshold,
            "models_used": result['models_used'],
            "individual_results": result['individual_results'],
            "total_models_used": len(result['models_used']),
            "detection_method": "all_models",
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"All models detection: {result['prediction']} with {len(result['models_used'])} models")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in all models detection: {str(e)}")
        return jsonify({
            "error": "Failed to analyze text with all models",
            "success": False
        }), 500

@app.route('/detect_selected', methods=['POST'])
def detect_selected_models_handler():
    """Detect AI text using specific selected models"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        models = data.get('models', [])
        threshold = data.get('threshold', 0.7)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if not models or not isinstance(models, list):
            return jsonify({"error": "Models list is required"}), 400
        
        if len(text) < 20:
            return jsonify({"error": "Text must be at least 20 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 10000 to 50000
            return jsonify({"error": "Text must be less than 50,000 characters"}), 400
        
        # Use selected models
        result = detect_with_selected_models(text, models)
        is_ai = result['ensemble_ai_probability'] > threshold
        
        response = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_ai_generated": is_ai,
            "ai_probability": result['ensemble_ai_probability'],
            "human_probability": result['ensemble_human_probability'],
            "prediction": result['prediction'],
            "confidence": result['confidence'],
            "threshold_used": threshold,
            "models_requested": models,
            "models_used": result['models_used'],
            "individual_results": result['individual_results'],
            "detection_method": "selected_models",
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Selected models detection: {result['prediction']} with models {result['models_used']}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in selected models detection: {str(e)}")
        return jsonify({
            "error": "Failed to analyze text with selected models",
            "success": False
        }), 500

@app.route('/detect_top_models', methods=['POST'])
def detect_top_models_handler():
    """Detect AI text using top N models based on criteria"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        n = data.get('n', 3)
        criteria = data.get('criteria', 'performance')
        threshold = data.get('threshold', 0.7)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if not isinstance(n, int) or n < 1 or n > 8:
            return jsonify({"error": "n must be an integer between 1 and 8"}), 400
        
        if criteria not in ['performance', 'speed', 'accuracy']:
            return jsonify({"error": "criteria must be 'performance', 'speed', or 'accuracy'"}), 400
        
        if len(text) < 20:
            return jsonify({"error": "Text must be at least 20 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 10000 to 50000
            return jsonify({"error": "Text must be less than 50,000 characters"}), 400
        
        # Use top N models
        result = detect_with_top_models(text, n=n, criteria=criteria)
        is_ai = result['ensemble_ai_probability'] > threshold
        
        response = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_ai_generated": is_ai,
            "ai_probability": result['ensemble_ai_probability'],
            "human_probability": result['ensemble_human_probability'],
            "prediction": result['prediction'],
            "confidence": result['confidence'],
            "threshold_used": threshold,
            "models_used": result['models_used'],
            "individual_results": result['individual_results'],
            "selection_criteria": criteria,
            "top_n": n,
            "detection_method": f"top_{n}_{criteria}",
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Top {n} {criteria} models detection: {result['prediction']}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in top models detection: {str(e)}")
        return jsonify({
            "error": "Failed to analyze text with top models",
            "success": False
        }), 500

@app.route('/detect_lines', methods=['POST'])
def detect_lines_handler():
    """Detect which specific lines in text are AI-generated"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        min_line_length = data.get('min_line_length', 20)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long for line detection"}), 400
        
        if len(text) > 15000:
            return jsonify({"error": "Text must be less than 15,000 characters for line detection"}), 400
        
        # Detect AI lines
        detector = AITextDetector()
        result = detector.detect_ai_lines(text, threshold, min_line_length)
        
        response = {
            "ai_detected_lines": result['ai_detected_lines'],
            "human_lines": result['human_lines'],
            "line_analysis": result['line_analysis'],
            "statistics": result['statistics'],
            "threshold_used": result['threshold_used'],
            "min_line_length": min_line_length,
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Line detection: {result['statistics']['ai_generated_lines']}/{result['statistics']['total_lines_analyzed']} lines detected as AI")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in line detection: {str(e)}")
        return jsonify({
            "error": "Failed to detect AI lines",
            "success": False
        }), 500

@app.route('/detect_sentences', methods=['POST'])
def detect_sentences_handler():
    """Detect which specific sentences in text are AI-generated"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long for sentence detection"}), 400
        
        if len(text) > 15000:
            return jsonify({"error": "Text must be less than 15,000 characters for sentence detection"}), 400
        
        # Detect AI sentences
        detector = AITextDetector()
        result = detector.detect_ai_sentences(text, threshold)
        
        response = {
            "ai_detected_sentences": result['ai_detected_sentences'],
            "human_sentences": result['human_sentences'],
            "sentence_analysis": result['sentence_analysis'],
            "statistics": result['statistics'],
            "threshold_used": result['threshold_used'],
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Sentence detection: {result['statistics']['ai_generated_sentences']}/{result['statistics']['total_sentences_analyzed']} sentences detected as AI")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in sentence detection: {str(e)}")
        return jsonify({
            "error": "Failed to detect AI sentences",
            "success": False
        }), 500

@app.route('/highlight_ai', methods=['POST'])
def highlight_ai_handler():
    """Highlight AI-detected portions in text"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        output_format = data.get('format', 'markdown')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if output_format not in ['markdown', 'html', 'plain']:
            return jsonify({"error": "format must be 'markdown', 'html', or 'plain'"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long for highlighting"}), 400
        
        if len(text) > 15000:
            return jsonify({"error": "Text must be less than 15,000 characters for highlighting"}), 400
        
        # Highlight AI text
        highlighted_text = highlight_ai_text(text, threshold, output_format)
        
        # Also get sentence analysis for additional info
        detector = AITextDetector()
        sentence_result = detector.detect_ai_sentences(text, threshold)
        
        response = {
            "original_text": text,
            "highlighted_text": highlighted_text,
            "output_format": output_format,
            "threshold_used": threshold,
            "ai_sentences_count": len(sentence_result['ai_detected_sentences']),
            "total_sentences": len(sentence_result['sentence_analysis']),
            "ai_percentage": sentence_result['statistics']['ai_percentage'],
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Text highlighting completed: {len(sentence_result['ai_detected_sentences'])} AI sentences highlighted")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in text highlighting: {str(e)}")
        return jsonify({
            "error": "Failed to highlight AI text",
            "success": False
        }), 500

@app.route('/get_ai_lines_simple', methods=['POST'])
def get_ai_lines_simple_handler():
    """Simple endpoint to get just the AI-detected lines with line numbers"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        min_line_length = data.get('min_line_length', 20)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long"}), 400
        
        # Get full AI lines detection result
        detector = AITextDetector()
        result = detector.detect_ai_lines(text, threshold, min_line_length)
        
        response = {
            "ai_lines": result['ai_detected_lines'],  # Full details with line numbers
            "ai_lines_count": len(result['ai_detected_lines']),
            "ai_lines_text_only": [line['text'] for line in result['ai_detected_lines']],
            "threshold_used": threshold,
            "min_line_length": min_line_length,
            "text_length": len(text),
            "statistics": result['statistics'],
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting AI lines: {str(e)}")
        return jsonify({
            "error": "Failed to get AI lines",
            "success": False
        }), 500

@app.route('/get_ai_sentences_simple', methods=['POST'])
def get_ai_sentences_simple_handler():
    """Simple endpoint to get just the AI-detected sentences"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long"}), 400
        
        # Get AI sentences
        ai_sentences = get_ai_sentences(text, threshold)
        
        response = {
            "ai_sentences": ai_sentences,
            "ai_sentences_count": len(ai_sentences),
            "threshold_used": threshold,
            "text_length": len(text),
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting AI sentences: {str(e)}")
        return jsonify({
            "error": "Failed to get AI sentences",
            "success": False
        }), 500

@app.route('/detect_models', methods=['GET'])
def get_detection_models_endpoint():
    """Get available AI detection models with enhanced information"""
    try:
        available_models = get_detection_models()
        
        model_info = {
            "roberta-base-openai-detector": {
                "name": "roberta-base-openai-detector",
                "description": "OpenAI's RoBERTa base detector",
                "type": "base",
                "performance_rank": 4,
                "speed_rank": 1,
                "accuracy_rank": 4
            },
            "roberta-large-openai-detector": {
                "name": "roberta-large-openai-detector", 
                "description": "OpenAI's RoBERTa large detector",
                "type": "large",
                "performance_rank": 2,
                "speed_rank": 5,
                "accuracy_rank": 2
            },
            "chatgpt-detector": {
                "name": "chatgpt-detector",
                "description": "Specialized ChatGPT detector",
                "type": "specialized",
                "performance_rank": 3,
                "speed_rank": 3,
                "accuracy_rank": 3
            },
            "mixed-detector": {
                "name": "mixed-detector",
                "description": "Mixed AI content detector",
                "type": "general",
                "performance_rank": 1,
                "speed_rank": 4,
                "accuracy_rank": 1
            },
            "multilingual-detector": {
                "name": "multilingual-detector",
                "description": "Multilingual AI detection",
                "type": "multilingual",
                "performance_rank": 5,
                "speed_rank": 6,
                "accuracy_rank": 5
            },
            "distilbert-detector": {
                "name": "distilbert-detector",
                "description": "Fast DistilBERT-based detector",
                "type": "fast",
                "performance_rank": 6,
                "speed_rank": 2,
                "accuracy_rank": 6
            },
            "bert-detector": {
                "name": "bert-detector",
                "description": "BERT-based classification detector",
                "type": "classification",
                "performance_rank": 7,
                "speed_rank": 7,
                "accuracy_rank": 7
            }
        }
        
        detailed_models = [model_info.get(model, {"name": model, "description": "Unknown model"}) for model in available_models]
        
        return jsonify({
            "available_models": detailed_models,
            "total_models": len(available_models),
            "default_ensemble": ["chatgpt-detector", "mixed-detector"],
            "recommended_single": "mixed-detector",
            "recommended_fast": "roberta-base-openai-detector",
            "recommended_accurate": "mixed-detector",
            "selection_criteria": {
                "performance": "Best overall detection capability",
                "speed": "Fastest processing time",
                "accuracy": "Most accurate detection"
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting detection models: {str(e)}")
        return jsonify({
            "error": "Failed to get detection models",
            "success": False
        }), 500

@app.route('/humanize_and_check', methods=['POST'])
def humanize_and_check_handler():
    """Humanize text and then check if it passes AI detection"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        # Extract humanization options
        use_paraphrasing = data.get("paraphrasing", True)
        use_enhanced = data.get("enhanced", True)
        paraphrase_model = data.get("model", None)
        detection_threshold = data.get("detection_threshold", 0.7)
        
        # Step 1: Check original text
        logger.info("Checking original text for AI detection")
        original_detection = detect_ai_text(text, method="ensemble")
        original_is_ai, original_confidence = is_ai_generated(text, detection_threshold)
        
        # Step 2: Humanize the text
        logger.info("Humanizing text")
        humanized_text, humanization_stats = humanizer_service.humanize_text(
            text=text,
            use_paraphrasing=use_paraphrasing,
            use_enhanced_rewriting=use_enhanced,
            paraphrase_model=paraphrase_model
        )
        
        # Step 3: Check humanized text
        logger.info("Checking humanized text for AI detection")
        humanized_detection = detect_ai_text(humanized_text, method="ensemble")
        humanized_is_ai, humanized_confidence = is_ai_generated(humanized_text, detection_threshold)
        
        # Calculate improvement
        ai_prob_reduction = original_detection['ensemble_ai_probability'] - humanized_detection['ensemble_ai_probability']
        detection_improved = original_is_ai and not humanized_is_ai
        
        response = {
            "original_text": text,
            "humanized_text": humanized_text,
            "humanization_stats": humanization_stats,
            "original_detection": {
                "is_ai_generated": original_is_ai,
                "ai_probability": original_detection['ensemble_ai_probability'],
                "prediction": original_detection['prediction'],
                "confidence": original_confidence
            },
            "humanized_detection": {
                "is_ai_generated": humanized_is_ai,
                "ai_probability": humanized_detection['ensemble_ai_probability'],
                "prediction": humanized_detection['prediction'],
                "confidence": humanized_confidence
            },
            "improvement": {
                "detection_improved": detection_improved,
                "ai_probability_reduction": ai_prob_reduction,
                "percentage_improvement": (ai_prob_reduction / original_detection['ensemble_ai_probability'] * 100) if original_detection['ensemble_ai_probability'] > 0 else 0
            },
            "threshold_used": detection_threshold,
            "success": True
        }
        
        logger.info(f"Humanization and detection completed. Improved: {detection_improved}, Reduction: {ai_prob_reduction:.3f}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in humanize and check: {str(e)}")
        return jsonify({
            "error": "Failed to humanize and check text",
            "success": False
        }), 500

# Legacy endpoint for backward compatibility
@app.route('/rewrite', methods=['POST'])
def rewrite_handler():
    """Legacy endpoint - redirects to humanize"""
    logger.info("Legacy /rewrite endpoint called, redirecting to /humanize")
    return humanize_handler()

@app.route('/get_ai_lines_detailed', methods=['POST'])
def get_ai_lines_detailed_handler():
    """Get detailed AI-detected lines with line numbers and probabilities"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        min_line_length = data.get('min_line_length', 20)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long"}), 400
        
        # Get full AI lines detection result
        detector = AITextDetector()
        result = detector.detect_ai_lines(text, threshold, min_line_length)
        
        # Format the AI lines with more readable structure
        formatted_ai_lines = []
        for line in result['ai_detected_lines']:
            formatted_ai_lines.append({
                "line_number": line['line_number'],
                "text": line['text'],
                "ai_probability": round(line['ai_probability'], 3),
                "confidence_level": "High" if line['ai_probability'] > 0.8 else "Medium" if line['ai_probability'] > 0.7 else "Low"
            })
        
        response = {
            "ai_detected_lines": formatted_ai_lines,
            "summary": {
                "total_lines_in_text": len(text.split('\n')),
                "lines_analyzed": result['statistics']['total_lines_analyzed'],
                "ai_lines_found": result['statistics']['ai_generated_lines'],
                "ai_percentage": round(result['statistics']['ai_percentage'], 2)
            },
            "settings": {
                "threshold_used": threshold,
                "min_line_length": min_line_length
            },
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting detailed AI lines: {str(e)}")
        return jsonify({
            "error": "Failed to get detailed AI lines",
            "success": False
        }), 500

if __name__ == '__main__':
    logger.info("Starting Humanize AI Server...")
    
    # Check if paraphrasing is available
    current_model = get_current_model()
    logger.info(f"Paraphrasing available: {current_model is not None}")
    if current_model:
        logger.info(f"Current model: {current_model}")
        logger.info(f"Device: {get_device_info()}")
    
    app.run(debug=False, host='0.0.0.0', port=8080)