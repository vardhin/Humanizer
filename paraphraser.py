import os
import logging
import torch
from typing import Tuple, Optional, List

# Suppress warnings
os.environ["TORCH_DYNAMO_DISABLE"] = "1"
os.environ["BITSANDBYTES_NOWELCOME"] = "1"

logger = logging.getLogger(__name__)

# Global variables for model management
current_model = None
model_name = None
device = None
tokenizer = None
model = None

# Model configurations with fallback options
MODEL_CONFIGS = {
    # T5 models (require sentencepiece)
    "t5-small": {
        "requires_sentencepiece": True,
        "model_name": "t5-small",
        "prefix": "paraphrase: ",
        "max_length": 512,
        "num_beams": 4,
        "do_sample": True,
        "temperature": 0.7,
        "top_k": 50
    },
    "t5-base": {
        "requires_sentencepiece": True,
        "model_name": "t5-base",
        "prefix": "paraphrase: ",
        "max_length": 512,
        "num_beams": 4,
        "do_sample": True,
        "temperature": 0.7,
        "top_k": 50
    },
    "Vamsi/T5_Paraphrase_Paws": {
        "requires_sentencepiece": True,
        "model_name": "Vamsi/T5_Paraphrase_Paws",
        "prefix": "paraphrase: ",
        "max_length": 512,
        "num_beams": 4,
        "do_sample": True,
        "temperature": 0.7,
        "top_k": 50
    },
    "humarin/chatgpt_paraphraser_on_T5_base": {
        "requires_sentencepiece": True,
        "model_name": "humarin/chatgpt_paraphraser_on_T5_base",
        "prefix": "paraphrase: ",
        "max_length": 512,
        "num_beams": 4,
        "do_sample": True,
        "temperature": 0.7,
        "top_k": 50
    },
    # BART models (don't require sentencepiece)
    "facebook/bart-base": {
        "requires_sentencepiece": False,
        "model_name": "facebook/bart-base",
        "prefix": "",
        "max_length": 512,
        "num_beams": 4,
        "do_sample": True,
        "temperature": 0.7,
        "top_k": 50
    },
    "facebook/bart-large": {
        "requires_sentencepiece": False,
        "model_name": "facebook/bart-large",
        "prefix": "",
        "max_length": 512,
        "num_beams": 4,
        "do_sample": True,
        "temperature": 0.7,
        "top_k": 50
    },
    # Pegasus models (alternative option)
    "tuner007/pegasus_paraphrase": {
        "requires_sentencepiece": False,
        "model_name": "tuner007/pegasus_paraphrase",
        "prefix": "",
        "max_length": 256,
        "num_beams": 10,
        "do_sample": True,
        "temperature": 0.8,
        "top_k": 40
    }
}

def get_device_info():
    """Get device information"""
    if torch.cuda.is_available():
        return f"CUDA ({torch.cuda.get_device_name()})"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "MPS (Apple Silicon)"
    else:
        return "CPU"

def check_sentencepiece_available():
    """Check if sentencepiece is available"""
    try:
        import sentencepiece
        return True
    except ImportError:
        return False

def get_available_models() -> List[str]:
    """Return list of available models based on installed dependencies"""
    available = []
    sentencepiece_available = check_sentencepiece_available()
    
    for model_key, config in MODEL_CONFIGS.items():
        if config["requires_sentencepiece"] and not sentencepiece_available:
            continue
        available.append(model_key)
    
    return available

def get_current_model() -> Optional[str]:
    """Get currently loaded model name"""
    return model_name if current_model is not None else None

def load_model(model_name_param: str = None) -> Tuple[bool, Optional[str]]:
    """
    Load a paraphrasing model with proper error handling and fallbacks
    """
    global current_model, model_name, device, tokenizer, model
    
    try:
        # Determine which model to load
        if model_name_param is None:
            # Try to find a working model
            available_models = get_available_models()
            if not available_models:
                return False, "No compatible models available. Please install sentencepiece."
            model_name_param = available_models[0]
        
        if model_name_param not in MODEL_CONFIGS:
            return False, f"Model {model_name_param} not supported"
        
        config = MODEL_CONFIGS[model_name_param]
        
        # Check sentencepiece requirement
        if config["requires_sentencepiece"] and not check_sentencepiece_available():
            return False, f"Model {model_name_param} requires sentencepiece. Please install it with: pip install sentencepiece"
        
        logger.info(f"Loading model: {model_name_param}")
        
        # Determine device
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        logger.info(f"Using device: {device}")
        
        # Load model based on type
        if config["requires_sentencepiece"]:
            # T5 models
            from transformers import T5Tokenizer, T5ForConditionalGeneration, pipeline
            tokenizer = T5Tokenizer.from_pretrained(config["model_name"])
            model = T5ForConditionalGeneration.from_pretrained(config["model_name"])
        else:
            # BART/Pegasus models
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
            tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
            model = AutoModelForSeq2SeqLM.from_pretrained(config["model_name"])
        
        # Move model to device
        model = model.to(device)
        
        # Create pipeline
        current_model = pipeline(
            "text2text-generation",
            model=model,
            tokenizer=tokenizer,
            device=0 if device == "cuda" else -1,
            max_length=config["max_length"],
            do_sample=config["do_sample"],
            temperature=config.get("temperature", 0.7)
        )
        
        model_name = model_name_param
        logger.info(f"Successfully loaded {model_name_param}")
        return True, None
        
    except Exception as e:
        error_msg = f"Error loading model {model_name_param}: {str(e)}"
        logger.error(error_msg)
        current_model = None
        model_name = None
        return False, error_msg

def paraphrase_text(text: str, model_name_param: str = None) -> Tuple[str, Optional[str]]:
    """
    Paraphrase text using the loaded model
    """
    global current_model, model_name
    
    try:
        # Load model if not loaded or different model requested
        if current_model is None or (model_name_param and model_name_param != model_name):
            success, error = load_model(model_name_param)
            if not success:
                return "", error
        
        if current_model is None:
            return "", "No model available for paraphrasing"
        
        # Get model config
        config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS["facebook/bart-base"])
        
        # Prepare input
        if config["prefix"]:
            input_text = f"{config['prefix']}{text}"
        else:
            input_text = text
        
        # Generate paraphrase
        result = current_model(
            input_text,
            max_length=min(len(text.split()) * 2 + 50, config["max_length"]),
            num_return_sequences=1,
            do_sample=config["do_sample"],
            temperature=config.get("temperature", 0.7),
            num_beams=config.get("num_beams", 4)
        )
        
        if result and len(result) > 0:
            paraphrased = result[0]['generated_text'].strip()
            
            # Clean up output if it contains the prefix
            if config["prefix"] and paraphrased.startswith(config["prefix"]):
                paraphrased = paraphrased[len(config["prefix"]):].strip()
            
            return paraphrased, None
        else:
            return "", "No paraphrase generated"
            
    except Exception as e:
        error_msg = f"Error in paraphrasing: {str(e)}"
        logger.error(error_msg)
        return "", error_msg

def initialize_paraphraser():
    """Initialize the paraphraser with error handling and fallbacks"""
    try:
        available_models = get_available_models()
        
        if not available_models:
            logger.warning("No compatible models available")
            logger.info("To enable T5 models, install sentencepiece: pip install sentencepiece")
            return
        
        # Try to load the first available model
        success, error = load_model(available_models[0])
        if success:
            logger.info(f"Paraphraser initialized successfully with {model_name}")
        else:
            logger.warning(f"Paraphraser initialization failed: {error}")
            logger.info("Paraphraser will run without AI model support")
    except Exception as e:
        logger.error(f"Failed to initialize paraphraser: {str(e)}")

# Initialize on import
initialize_paraphraser()
