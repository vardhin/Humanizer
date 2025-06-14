import os
import json
import time
from typing import Dict, Tuple
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Import our utility modules
from paraphraser import paraphrase_text, load_model, get_available_models, get_current_model, get_device_info
from rewriter import rewrite_text, get_synonym, refine_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

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
        
        if len(text) > 5000:
            return jsonify({"error": "Text must be less than 5000 characters"}), 400
        
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
        
        if len(text) > 5000:
            return jsonify({"error": "Text must be less than 5000 characters"}), 400
        
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
        
        return jsonify({
            'rewritten_text': rewritten_text or text,
            'success': True,
            'original_text': text,
            'statistics': {
                'original_length': len(text),
                'rewritten_length': len(rewritten_text) if rewritten_text else len(text),
                'length_change': (len(rewritten_text) if rewritten_text else len(text)) - len(text),
                'enhanced_rewriting_used': enhanced
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
        
        if len(text) > 5000:
            return jsonify({"error": "Text must be less than 5000 characters"}), 400
        
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
        
        if len(text) > 5000:
            return jsonify({"error": "Text must be less than 5000 characters"}), 400
        
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

# Legacy endpoint for backward compatibility
@app.route('/rewrite', methods=['POST'])
def rewrite_handler():
    """Legacy endpoint - redirects to humanize"""
    logger.info("Legacy /rewrite endpoint called, redirecting to /humanize")
    return humanize_handler()

if __name__ == '__main__':
    logger.info("Starting Humanize AI Server...")
    
    # Check if paraphrasing is available
    current_model = get_current_model()
    logger.info(f"Paraphrasing available: {current_model is not None}")
    if current_model:
        logger.info(f"Current model: {current_model}")
        logger.info(f"Device: {get_device_info()}")
    
    app.run(debug=False, host='0.0.0.0', port=8080)