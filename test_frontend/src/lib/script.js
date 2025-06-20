import { writable } from 'svelte/store';

// Create stores for reactive state
export const inputText = writable('');
export const isProcessing = writable(false);
export const currentStep = writable('');
export const error = writable(null);
export const results = writable({
    paraphrased: '',
    rewritten: '',
    final: ''
});
export const statistics = writable({});
export const processingSteps = writable([]);

// Multi-model results
export const multiResults = writable(null);
export const allResults = writable(null);
export const showMultiResults = writable(false);

// Configuration
export const availableModels = writable([]);
export const currentModel = writable('');
export const selectedModel = writable('');
export const useEnhanced = writable(true); // Changed default to true
export const backendStatus = writable(null);

// Processing modes
export const processingMode = writable('single');

// AI Detection state
export const detectionResults = writable(null);
export const isDetecting = writable(false);
export const detectionMode = writable('ensemble');
export const selectedDetectionModel = writable('mixed-detector'); // Changed default
export const detectionThreshold = writable(0.7);
export const segmentLength = writable(200);
export const availableDetectionModels = writable([]);
export const showDetectionResults = writable(false);

// Enhanced AI Detection features - removed sentence-related stores
export const lineDetectionResults = writable(null);
export const highlightedText = writable('');
export const detectionFormat = writable('markdown');
export const useAllDetectionModels = writable(false);
export const topNModels = writable(3);
export const detectionCriteria = writable('performance');
export const minLineLength = writable(20);

// Combined processing state
export const combinedResults = writable(null);
export const showCombinedResults = writable(false);

// Toast notification system
export const toastMessage = writable('');
export const toastType = writable('success');
export const showToastFlag = writable(false);

// API base URL
const API_BASE = 'http://localhost:8080';

// Error logging function
export function logError(context, error, additionalData = {}) {
    const errorLog = {
        timestamp: new Date().toISOString(),
        context: context,
        error: error.message || error.toString(),
        stack: error.stack,
        url: typeof window !== 'undefined' ? window.location.href : 'server-side',
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'server-side',
        additionalData: additionalData
    };
    
    console.error(`[${context}] Error:`, errorLog);
    return errorLog;
}

// Copy to clipboard functionality
export async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!');
    } catch (err) {
        logError('copyToClipboard', err, { textLength: text.length });
        console.error('Failed to copy: ', err);
        showToast('Failed to copy to clipboard', 'error');
    }
}

// Toast notification system
export function showToast(message, type = 'success') {
    toastMessage.set(message);
    toastType.set(type);
    showToastFlag.set(true);
    setTimeout(() => {
        showToastFlag.set(false);
    }, 3000);
}

// Load backend status and models
export async function loadBackendInfo() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            const status = await response.json();
            backendStatus.set(status);
        } else {
            throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
        }

        const modelsResponse = await fetch(`${API_BASE}/models`);
        if (modelsResponse.ok) {
            const modelsData = await modelsResponse.json();
            availableModels.set(modelsData.available_models || []);
            currentModel.set(modelsData.current_model || '');
            selectedModel.set(modelsData.current_model || '');
        } else {
            throw new Error(`Models fetch failed: ${modelsResponse.status} ${modelsResponse.statusText}`);
        }
    } catch (err) {
        logError('loadBackendInfo', err, { API_BASE });
        console.error('Failed to load backend info:', err);
        error.set('Failed to connect to backend service');
    }
}

// Load specific model
export async function loadModel(modelName) {
    let current;
    currentModel.subscribe(value => current = value)();
    
    if (!modelName || modelName === current) return;

    try {
        const response = await fetch(`${API_BASE}/load_model`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: modelName })
        });

        if (response.ok) {
            const data = await response.json();
            currentModel.set(data.current_model);
            showToast(`Model ${modelName} loaded successfully`);
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to load model: ${response.status}`);
        }
    } catch (err) {
        logError('loadModel', err, { modelName, current });
        console.error('Failed to load model:', err);
        showToast(`Failed to load model: ${err.message}`, 'error');
    }
}

// Validate input text - updated length limits
export function validateInput(text) {
    if (!text.trim()) {
        showToast('Please enter some text to humanize', 'error');
        return false;
    }

    if (text.length < 10) {
        showToast('Text must be at least 10 characters long', 'error');
        return false;
    }

    if (text.length > 50000) { // Changed from 5000 to 50000
        showToast('Text must be less than 50,000 characters', 'error');
        return false;
    }

    return true;
}

// Enhanced function for validating detection input text
export function validateDetectionInput(text) {
    if (!text.trim()) {
        showToast('Please enter some text to analyze', 'error');
        return false;
    }

    if (text.length < 20) {
        showToast('Text must be at least 20 characters long for detection', 'error');
        return false;
    }

    if (text.length > 50000) {
        showToast('Text must be less than 50,000 characters for detection', 'error');
        return false;
    }

    return true;
}

// Reset results
export function resetResults() {
    results.set({ paraphrased: '', rewritten: '', final: '' });
    statistics.set({});
    processingSteps.set([]);
    multiResults.set(null);
    allResults.set(null);
    showMultiResults.set(false);
    error.set(null);
}

// Reset detection results
export function resetDetectionResults() {
    detectionResults.set(null);
    lineDetectionResults.set(null);
    highlightedText.set('');
    showDetectionResults.set(false);
    error.set(null);
}

// Single model humanization (paraphrase + rewrite)
export async function humanizeWithSingleModel(text, selected, enhanced) {
    if (!validateInput(text)) return;

    isProcessing.set(true);
    currentStep.set('');
    resetResults();
    processingMode.set('single');

    try {
        let current;
        currentModel.subscribe(value => current = value)();
        
        // Load selected model if different from current
        if (selected && selected !== current) {
            await loadModel(selected);
        }

        // Step 1: Paraphrasing
        currentStep.set('paraphrasing');
        const paraphraseResponse = await fetch(`${API_BASE}/paraphrase_only`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                model: selected
            })
        });

        if (paraphraseResponse.ok) {
            const paraphraseData = await paraphraseResponse.json();
            results.update(r => ({ ...r, paraphrased: paraphraseData.paraphrased_text }));
            statistics.update(s => ({ ...s, ...paraphraseData.statistics }));
            
            // Show paraphrased result briefly
            await new Promise(resolve => setTimeout(resolve, 1000));
        } else {
            const errorData = await paraphraseResponse.json();
            throw new Error(errorData.error || 'Paraphrasing failed');
        }

        // Step 2: Rewriting
        currentStep.set('rewriting');
        let paraphrased;
        results.subscribe(r => paraphrased = r.paraphrased)();
        
        const rewriteResponse = await fetch(`${API_BASE}/rewrite_only`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: paraphrased,
                enhanced: enhanced
            })
        });

        if (rewriteResponse.ok) {
            const rewriteData = await rewriteResponse.json();
            results.update(r => ({ 
                ...r, 
                rewritten: rewriteData.rewritten_text,
                final: rewriteData.rewritten_text 
            }));
            statistics.update(s => ({ 
                ...s, 
                ...rewriteData.statistics,
                final_length: rewriteData.statistics.rewritten_length,
                enhanced_rewriting_used: enhanced
            }));
            
            currentStep.set('complete');
            showToast('Text humanized successfully!');
        } else {
            const errorData = await rewriteResponse.json();
            throw new Error(errorData.error || 'Rewriting failed');
        }

    } catch (err) {
        logError('humanizeWithSingleModel', err, { 
            inputLength: text.length,
            enhanced,
            selected
        });
        error.set(err.message);
        showToast(err.message, 'error');
    } finally {
        isProcessing.set(false);
        currentStep.set('complete');
    }
}

// Multi-model paraphrasing (2 best models in pipeline)
export async function paraphraseWithMultiModels(text) {
    if (!validateInput(text)) return;

    isProcessing.set(true);
    currentStep.set('paraphrasing');
    resetResults();
    processingMode.set('multi');

    try {
        const response = await fetch(`${API_BASE}/paraphrase_multi`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });

        if (response.ok) {
            const data = await response.json();
            multiResults.set(data);
            showMultiResults.set(true);
            showToast(`Pipeline completed! ${data.statistics.successful_steps}/${data.statistics.pipeline_steps} steps successful.`);
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || `Multi-model paraphrasing failed: ${response.status}`);
        }
    } catch (err) {
        logError('paraphraseWithMultiModels', err, { 
            inputLength: text.length,
            processingMode: 'multi' 
        });
        error.set(err.message);
        showToast(err.message, 'error');
    } finally {
        isProcessing.set(false);
        currentStep.set('complete');
    }
}

// All models paraphrasing (all models in pipeline)
export async function paraphraseWithAllModels(text) {
    if (!validateInput(text)) return;

    isProcessing.set(true);
    currentStep.set('paraphrasing');
    resetResults();
    processingMode.set('all');

    try {
        const response = await fetch(`${API_BASE}/paraphrase_all`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });

        if (response.ok) {
            const data = await response.json();
            allResults.set(data);
            showMultiResults.set(true);
            showToast(`Pipeline completed! ${data.statistics.successful_steps}/${data.statistics.pipeline_steps} steps successful in ${data.statistics.total_processing_time}s.`);
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || `All-models paraphrasing failed: ${response.status}`);
        }
    } catch (err) {
        logError('paraphraseWithAllModels', err, { 
            inputLength: text.length,
            processingMode: 'all'
        });
        error.set(err.message);
        showToast(err.message, 'error');
    } finally {
        isProcessing.set(false);
        currentStep.set('complete');
    }
}

// Continue a paraphrased result to rewriting
export async function continueToRewrite(paraphrasedText, modelUsed = null, enhanced, originalText) {
    isProcessing.set(true);
    currentStep.set('rewriting');
    showMultiResults.set(false);
    
    // Set the paraphrased result
    results.update(r => ({
        ...r,
        paraphrased: paraphrasedText,
        rewritten: '',
        final: ''
    }));

    try {
        const rewriteResponse = await fetch(`${API_BASE}/rewrite_only`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: paraphrasedText,
                enhanced: enhanced
            })
        });

        if (rewriteResponse.ok) {
            const rewriteData = await rewriteResponse.json();
            results.update(r => ({
                ...r,
                rewritten: rewriteData.rewritten_text,
                final: rewriteData.rewritten_text
            }));
            statistics.set({ 
                ...rewriteData.statistics,
                final_length: rewriteData.statistics.rewritten_length,
                enhanced_rewriting_used: enhanced,
                model_used: modelUsed,
                original_length: originalText ? originalText.length : 0,
                paraphrased_length: paraphrasedText.length
            });
            
            showToast('Text humanized successfully!');
        } else {
            const errorData = await rewriteResponse.json();
            throw new Error(errorData.error || 'Rewriting failed');
        }
    } catch (err) {
        logError('continueToRewrite', err, { enhanced });
        error.set(err.message);
        showToast(err.message, 'error');
    } finally {
        isProcessing.set(false);
        currentStep.set('complete');
    }
}

// Load available detection models with enhanced information
export async function loadDetectionModels() {
    try {
        const response = await fetch(`${API_BASE}/detect_models`);
        if (response.ok) {
            const data = await response.json();
            availableDetectionModels.set(data.available_models || []);
        } else {
            console.warn('Failed to load detection models');
        }
    } catch (err) {
        logError('loadDetectionModels', err);
        console.warn('Failed to load detection models:', err);
    }
}

// Enhanced AI Detection with multiple modes - updated for new backend structure
export async function detectAIText(text, mode = 'ensemble', threshold = 0.7, options = {}) {
    if (!validateDetectionInput(text)) return;

    isDetecting.set(true);
    resetDetectionResults();
    error.set(null);

    try {
        let endpoint = '/detect';
        let requestBody = {
            text: text,
            threshold: threshold
        };

        // Configure request based on mode and options
        switch (mode) {
            case 'ensemble':
                endpoint = '/detect';
                if (options.useAllModels) {
                    requestBody.use_all_models = true;
                } else if (options.topN) {
                    requestBody.top_n = options.topN;
                    requestBody.criteria = options.criteria || 'performance';
                } else if (options.selectedModels) {
                    requestBody.models = options.selectedModels;
                }
                break;
            case 'all_models':
                endpoint = '/detect_all_models';
                break;
            case 'selected':
                endpoint = '/detect_selected';
                requestBody.models = options.selectedModels || [selectedDetectionModel.get()];
                break;
            case 'top_models':
                endpoint = '/detect_top_models';
                requestBody.n = options.topN || 3;
                requestBody.criteria = options.criteria || 'performance';
                break;
            case 'single':
                endpoint = '/detect_selected';
                requestBody.models = [options.selectedModel || selectedDetectionModel.get()];
                break;
            case 'segments':
                endpoint = '/detect_lines'; // Updated to use detect_lines for segment analysis
                requestBody.min_line_length = options.segmentLength || 200;
                break;
            default:
                endpoint = '/detect';
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (response.ok) {
            const data = await response.json();
            data.mode = mode;
            detectionResults.set(data);
            showDetectionResults.set(true);
            
            const prediction = data.prediction || (data.is_ai_generated ? 'AI-generated' : 'Human-written');
            showToast(`Detection complete: ${prediction} (${(data.ai_probability * 100).toFixed(1)}%)`);
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || `Detection failed: ${response.status}`);
        }
    } catch (err) {
        logError('detectAIText', err, { mode, inputLength: text.length, options });
        error.set(err.message);
        showToast(err.message, 'error');
    } finally {
        isDetecting.set(false);
    }
}

// Detect AI lines in text
export async function detectAILines(text, threshold = 0.6, minLineLength = 20) {
    if (!validateDetectionInput(text)) return;

    isDetecting.set(true);
    error.set(null);

    try {
        const response = await fetch(`${API_BASE}/detect_lines`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                threshold: threshold,
                min_line_length: minLineLength
            })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Fix: Properly transform the data to match frontend expectations
            const transformedData = {
                ...data,
                line_results: data.line_analysis.map(line => ({
                    line_number: line.line_number,
                    text: line.line_text,
                    ai_probability: line.ai_probability,
                    is_ai_generated: line.is_ai_generated,
                    confidence: line.confidence
                }))
            };
            
            lineDetectionResults.set(transformedData);
            
            const aiLinesCount = data.statistics.ai_generated_lines;
            const totalLines = data.statistics.total_lines_analyzed;
            showToast(`Line detection complete: ${aiLinesCount}/${totalLines} lines detected as AI`);
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Line detection failed');
        }
    } catch (err) {
        logError('detectAILines', err, { inputLength: text.length });
        error.set(err.message);
        showToast(err.message, 'error');
    } finally {
        isDetecting.set(false);
    }
}

// Enhanced highlight AI text function with better error handling
export async function highlightAIText(text, threshold = 0.6, format = 'markdown') {
    if (!validateDetectionInput(text)) return;

    isDetecting.set(true);
    error.set(null);
    highlightedText.set(''); // Reset highlighted text

    try {
        const response = await fetch(`${API_BASE}/highlight_ai`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                threshold: threshold,
                format: format
            })
        });

        if (response.ok) {
            const data = await response.json();
            // Ensure we have highlighted text
            if (data.highlighted_text && data.highlighted_text.trim()) {
                highlightedText.set(data.highlighted_text);
                const count = data.ai_sentences_count || 0;
                showToast(`Text highlighting complete: ${count} AI portions highlighted`);
            } else {
                highlightedText.set('No AI content detected for highlighting.');
                showToast('No AI content found to highlight');
            }
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Text highlighting failed');
        }
    } catch (err) {
        logError('highlightAIText', err, { inputLength: text.length, format, threshold });
        error.set(err.message);
        showToast(err.message, 'error');
        // Set fallback text
        highlightedText.set('Failed to highlight text. Please try again.');
    } finally {
        isDetecting.set(false);
    }
}

// Enhanced get AI lines function with better error handling
export async function getAILines(text, threshold = 0.6) {
    try {
        const response = await fetch(`${API_BASE}/get_ai_lines_simple`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                threshold: threshold
            })
        });

        if (response.ok) {
            const data = await response.json();
            const aiLines = data.ai_lines || [];
            
            // Fix: Ensure we return properly formatted lines
            return aiLines.map(line => {
                if (typeof line === 'object' && line !== null) {
                    return line.text || line.content || line.line || String(line);
                }
                return String(line);
            });
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to get AI lines');
        }
    } catch (err) {
        logError('getAILines', err, { inputLength: text.length, threshold });
        throw err;
    }
}

// Direct access to specific models/methods
export async function detectWithAllModels(text, threshold = 0.7) {
    return await detectAIText(text, 'all_models', threshold);
}

export async function detectWithSelectedModels(text, models, threshold = 0.7) {
    return await detectAIText(text, 'selected', threshold, { selectedModels: models });
}

export async function detectWithTopModels(text, n = 3, criteria = 'performance', threshold = 0.7) {
    return await detectAIText(text, 'top_models', threshold, { topN: n, criteria });
}

// Humanize and check combined function
export async function humanizeAndCheck(text, enhanced, selected, threshold) {
    if (!validateInput(text)) return;

    isProcessing.set(true);
    currentStep.set('humanizing and checking');
    combinedResults.set(null);
    showCombinedResults.set(false);
    error.set(null);

    try {
        const response = await fetch(`${API_BASE}/humanize_and_check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                paraphrasing: true,
                enhanced: enhanced,
                model: selected,
                detection_threshold: threshold
            })
        });

        if (response.ok) {
            const data = await response.json();
            combinedResults.set(data);
            showCombinedResults.set(true);
            
            const improved = data.improvement.detection_improved;
            const reduction = data.improvement.ai_probability_reduction;
            showToast(`Processing complete! ${improved ? 'Detection improved' : 'No detection improvement'} (${(reduction * 100).toFixed(1)}% reduction)`);
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || `Combined processing failed: ${response.status}`);
        }
    } catch (err) {
        logError('humanizeAndCheck', err, { inputLength: text.length });
        error.set(err.message);
        showToast(err.message, 'error');
    } finally {
        isProcessing.set(false);
        currentStep.set('complete');
    }
}

// Legacy function for backward compatibility
export async function detectAITextLegacy(text, mode, threshold, selectedModel, segLength) {
    const options = {
        selectedModel: selectedModel,
        segmentLength: segLength
    };
    
    return await detectAIText(text, mode, threshold, options);
}

// Updated detection model management - synced with backend
export function getDetectionModelInfo() {
    return {
        "roberta-base-openai-detector": {
            name: "RoBERTa Base",
            description: "Fast, lightweight detector",
            type: "base",
            speed: "★★★★★",
            accuracy: "★★★☆☆",
            performance_rank: 4,
            speed_rank: 1,
            accuracy_rank: 4
        },
        "roberta-large-openai-detector": {
            name: "RoBERTa Large", 
            description: "Balanced performance detector",
            type: "large",
            speed: "★★★☆☆",
            accuracy: "★★★★☆",
            performance_rank: 2,
            speed_rank: 5,
            accuracy_rank: 2
        },
        "chatgpt-detector": {
            name: "ChatGPT Detector",
            description: "Specialized for ChatGPT content",
            type: "specialized",
            speed: "★★★★☆",
            accuracy: "★★★☆☆",
            performance_rank: 3,
            speed_rank: 3,
            accuracy_rank: 3
        },
        "mixed-detector": {
            name: "Mixed Detector",
            description: "Best overall performance",
            type: "general",
            speed: "★★★☆☆",
            accuracy: "★★★★★",
            performance_rank: 1,
            speed_rank: 4,
            accuracy_rank: 1
        },
        "multilingual-detector": {
            name: "Multilingual Detector",
            description: "Multilingual AI detection",
            type: "multilingual",
            speed: "★★☆☆☆",
            accuracy: "★★☆☆☆",
            performance_rank: 5,
            speed_rank: 6,
            accuracy_rank: 5
        },
        "distilbert-detector": {
            name: "DistilBERT Detector",
            description: "Fast DistilBERT-based detector",
            type: "fast",
            speed: "★★★★☆",
            accuracy: "★★☆☆☆",
            performance_rank: 6,
            speed_rank: 2,
            accuracy_rank: 6
        },
        "bert-detector": {
            name: "BERT Detector",
            description: "BERT-based classification detector",
            type: "classification",
            speed: "★★☆☆☆",
            accuracy: "★★☆☆☆",
            performance_rank: 7,
            speed_rank: 7,
            accuracy_rank: 7
        }
    };
}

// Updated recommendation function
export function getRecommendedDetectionModel(type = 'performance') {
    const recommendations = {
        performance: 'mixed-detector', // Updated based on backend rankings
        speed: 'roberta-base-openai-detector',
        accuracy: 'mixed-detector', // Updated based on backend rankings
        general: 'mixed-detector'
    };
    
    return recommendations[type] || 'mixed-detector';
}

// New endpoint for detailed AI lines
export async function getDetailedAILines(text, threshold = 0.6, minLineLength = 20) {
    try {
        const response = await fetch(`${API_BASE}/get_ai_lines_detailed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                threshold: threshold,
                min_line_length: minLineLength
            })
        });

        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            throw new Error('Failed to get detailed AI lines');
        }
    } catch (err) {
        logError('getDetailedAILines', err);
        return null;
    }
}

// Initialize detection models on startup
loadDetectionModels();

// Updated humanization model management - synced with backend paraphraser.py
export function getHumanizationModelInfo() {
    return {
        "humarin/chatgpt_paraphraser_on_T5_base": {
            name: "ChatGPT Paraphraser T5",
            description: "Specialized for ChatGPT-style content paraphrasing",
            type: "specialized",
            speed: "★★★☆☆",
            accuracy: "★★★★★",
            performance_rank: 1,
            speed_rank: 3,
            accuracy_rank: 1,
            requires_sentencepiece: true
        },
        "Vamsi/T5_Paraphrase_Paws": {
            name: "T5 Paraphrase PAWS",
            description: "High-quality paraphrasing with diverse outputs",
            type: "paraphrase",
            speed: "★★★☆☆",
            accuracy: "★★★★☆",
            performance_rank: 2,
            speed_rank: 4,
            accuracy_rank: 2,
            requires_sentencepiece: true
        },
        "facebook/bart-large": {
            name: "BART Large",
            description: "Powerful sequence-to-sequence model for text generation",
            type: "large",
            speed: "★★☆☆☆",
            accuracy: "★★★★☆",
            performance_rank: 3,
            speed_rank: 6,
            accuracy_rank: 3,
            requires_sentencepiece: false
        },
        "tuner007/pegasus_paraphrase": {
            name: "Pegasus Paraphrase",
            description: "Abstractive summarization-based paraphrasing",
            type: "abstractive",
            speed: "★★★★☆",
            accuracy: "★★★☆☆",
            performance_rank: 4,
            speed_rank: 2,
            accuracy_rank: 5,
            requires_sentencepiece: false
        },
        "facebook/bart-base": {
            name: "BART Base",
            description: "Fast and efficient text generation model",
            type: "base",
            speed: "★★★★☆",
            accuracy: "★★★☆☆",
            performance_rank: 5,
            speed_rank: 2,
            accuracy_rank: 4,
            requires_sentencepiece: false
        },
        "t5-base": {
            name: "T5 Base",
            description: "General-purpose text-to-text transformer",
            type: "general",
            speed: "★★★★☆",
            accuracy: "★★★☆☆",
            performance_rank: 6,
            speed_rank: 2,
            accuracy_rank: 6,
            requires_sentencepiece: true
        },
        "t5-small": {
            name: "T5 Small",
            description: "Lightweight T5 model for basic paraphrasing",
            type: "lightweight",
            speed: "★★★★★",
            accuracy: "★★☆☆☆",
            performance_rank: 7,
            speed_rank: 1,
            accuracy_rank: 7,
            requires_sentencepiece: true
        }
    };
}

// Updated recommendation function for humanization models
export function getRecommendedHumanizationModel(type = 'performance') {
    const recommendations = {
        performance: 'humarin/chatgpt_paraphraser_on_T5_base',
        speed: 't5-small',
        accuracy: 'humarin/chatgpt_paraphraser_on_T5_base',
        general: 'Vamsi/T5_Paraphrase_Paws',
        quality: 'humarin/chatgpt_paraphraser_on_T5_base',
        fast: 'facebook/bart-base',
        balanced: 'Vamsi/T5_Paraphrase_Paws'
    };
    
    return recommendations[type] || 'humarin/chatgpt_paraphraser_on_T5_base';
}