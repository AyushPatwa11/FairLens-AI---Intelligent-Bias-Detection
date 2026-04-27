document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = (window.FAIRLENS_API_BASE || 'http://127.0.0.1:8001').replace(/\/$/, '');
    const apiUrl = (path) => `${API_BASE_URL}${path}`;

    // Safely escape HTML to prevent XSS when inserting untrusted text into innerHTML
    const escapeHtml = (str) => String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    // Convert a plain Markdown string (with HTML-escaped content) to safe HTML.
    // Only the structural Markdown patterns we produce are converted; no raw HTML passes through.
    const markdownToHtml = (md) => escapeHtml(md)
        .replace(/^### (.*$)/gim, '<h4>$1</h4>')
        .replace(/^## (.*$)/gim, '<h3 class="mt-3 mb-2">$1</h3>')
        .replace(/^# (.*$)/gim, '<h2 class="mt-4 mb-2">$1</h2>')
        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/gim, '<em>$1</em>')
        .replace(/\n/gim, '<br>');

    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.view-section');
    const pageTitle = document.getElementById('page-title');

    const titles = {
        'dashboard': 'Dashboard',
        'dataset-analyzer': 'Dataset Bias Analyzer',
        'jd-scanner': 'Job Description Bias Scanner',
        'profile-simulator': 'Individual Bias Simulator'
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove active class from all
            navItems.forEach(nav => nav.classList.remove('active'));
            sections.forEach(sec => sec.classList.remove('active'));

            // Add active class to clicked
            item.classList.add('active');
            const targetId = item.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
            pageTitle.textContent = titles[targetId];
        });
    });

    // -------------------------------------------------------------
    // MODE 1: Dataset Analyzer
    // -------------------------------------------------------------
    const csvFileInput = document.getElementById('csv-file-input');
    const datasetResults = document.getElementById('dataset-results');
    const runAnalysisBtn = document.getElementById('run-analysis-btn');
    const analysisDashboard = document.getElementById('analysis-dashboard');
    const applyMitigationBtn = document.getElementById('apply-mitigation-btn');
    const postMitigation = document.getElementById('post-mitigation');

    let currentCsvFile = null;
    csvFileInput.addEventListener('change', (e) => {
        if(e.target.files.length > 0) {
            currentCsvFile = e.target.files[0];
            const fileName = currentCsvFile.name;
            const uploadZone = document.getElementById('csv-upload');
            uploadZone.innerHTML = `
                <i class="ph ph-file-csv" style="color: var(--success-color)"></i>
                <h3>${fileName} Uploaded Successfully</h3>
                <p>Ready for analysis.</p>
                <button class="btn btn-outline mt-3" onclick="document.getElementById('csv-file-input').click()">Replace File</button>
            `;
            datasetResults.classList.remove('hidden');
            // Scroll to mapping
            datasetResults.scrollIntoView({ behavior: 'smooth' });
        }
    });

    runAnalysisBtn.addEventListener('click', async () => {
        if (!currentCsvFile) {
            alert('Please upload a CSV file first.');
            return;
        }
        runAnalysisBtn.disabled = true;
        runAnalysisBtn.innerHTML = '<i class="ph ph-spinner ph-spin"></i> Analyzing Metrics...';
        
        try {
            const formData = new FormData();
            formData.append('file', currentCsvFile);
            
            const targetMap = document.getElementById('target-map').value;
            const sensitiveSelect = document.getElementById('sensitive-map');
            const sensitiveMap = Array.from(sensitiveSelect.selectedOptions).map(opt => opt.value);
            
            formData.append('target', targetMap);
            formData.append('sensitive', JSON.stringify(sensitiveMap));
            
            const response = await fetch(apiUrl('/api/dataset/analyze'), {
                method: 'POST',
                body: formData
            });

            let result;
            if (!response.ok) {
                const text = await response.text();
                // Try to parse JSON error, otherwise show raw body
                try {
                    const parsed = JSON.parse(text || '{}');
                    alert('Analysis failed: ' + (parsed.error || JSON.stringify(parsed)));
                } catch (e) {
                    alert(`Analysis failed: ${response.status} ${response.statusText}\n${text}`);
                }
                runAnalysisBtn.disabled = false;
                runAnalysisBtn.innerHTML = 'Run Fairness Analysis';
                return;
            }

            try {
                result = await response.json();
            } catch (e) {
                const text = await response.text();
                alert('Analysis failed: invalid response from server. ' + text);
                runAnalysisBtn.disabled = false;
                runAnalysisBtn.innerHTML = 'Run Fairness Analysis';
                return;
            }

            if (result.success) {
                // Update score
                const scoreCircle = document.querySelector('#analysis-dashboard .score-circle');
                scoreCircle.textContent = result.score;
                let scoreClass = 'score-low';
                if (result.score > 40) scoreClass = 'score-high';
                else if (result.score > 20) scoreClass = 'score-medium';
                scoreCircle.className = `score-circle ${scoreClass}`;
                
                // Update feature importances (XAI)
                if (result.feature_importances) {
                    const chartContainer = document.getElementById('feature-importance-chart');
                    chartContainer.innerHTML = ''; // Clear old content
                    
                    // Find max absolute value for scaling
                    const maxAbs = Math.max(...Object.values(result.feature_importances).map(Math.abs));
                    
                    for (const [feature, weight] of Object.entries(result.feature_importances)) {
                        const isPositive = weight > 0;
                        const percentage = Math.max(5, (Math.abs(weight) / maxAbs) * 100);
                        
                        const barHtml = `
                            <div class="mb-2">
                                <div class="d-flex justify-content-between mb-1" style="font-size: 0.85rem;">
                                    <span>${feature.replace('_', ' ')}</span>
                                    <span class="${isPositive ? 'text-success' : 'text-danger'}">
                                        ${isPositive ? '+' : ''}${weight}
                                    </span>
                                </div>
                                <div class="progress" style="height: 8px;">
                                    <div class="progress-bar ${isPositive ? 'bg-success' : 'bg-danger'}" 
                                         role="progressbar" 
                                         style="width: ${percentage}%">
                                    </div>
                                </div>
                            </div>
                        `;
                        chartContainer.innerHTML += barHtml;
                    }
                }
                
                document.querySelector('#analysis-dashboard .score-details strong').textContent = result.risk;
                
                // Display AI Report
                if (result.ai_report) {
                    const reportPanel = document.getElementById('ai-report-panel');
                    const reportContent = document.getElementById('ai-report-content');
                    reportContent.innerHTML = markdownToHtml(result.ai_report);
                    reportPanel.style.display = 'block';
                }
                
                runAnalysisBtn.disabled = false;
                runAnalysisBtn.innerHTML = 'Analysis Complete';
                analysisDashboard.classList.remove('hidden');
                analysisDashboard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                alert('Analysis failed: ' + result.error);
                runAnalysisBtn.disabled = false;
                runAnalysisBtn.innerHTML = 'Run Fairness Analysis';
            }
        } catch (err) {
            alert('Failed to connect to backend API.');
            runAnalysisBtn.disabled = false;
            runAnalysisBtn.innerHTML = 'Run Fairness Analysis';
        }
    });

    applyMitigationBtn.addEventListener('click', async () => {
        applyMitigationBtn.disabled = true;
        applyMitigationBtn.innerHTML = '<i class="ph ph-spinner ph-spin"></i> Applying Reweighing...';
        
        try {
            const response = await fetch(apiUrl('/api/dataset/mitigate'), { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                const newScoreCircle = document.querySelector('#post-mitigation .score-circle');
                newScoreCircle.textContent = result.new_score;
                
                let scoreClass = 'score-low';
                if (result.new_score > 40) scoreClass = 'score-high';
                else if (result.new_score > 20) scoreClass = 'score-medium';
                newScoreCircle.className = `score-circle ${scoreClass}`;
                
                document.querySelector('#post-mitigation .score-details p').textContent = `Reduced by ${result.reduction} points`;
                
                applyMitigationBtn.disabled = false;
                applyMitigationBtn.innerHTML = 'Mitigation Applied';
                postMitigation.classList.remove('hidden');
            }
        } catch (err) {
            alert('Failed to apply mitigation.');
            applyMitigationBtn.disabled = false;
            applyMitigationBtn.innerHTML = 'Apply & Re-evaluate';
        }
    });

    // -------------------------------------------------------------
    // MODE 2: JD Scanner
    // -------------------------------------------------------------
    const scanJdBtn = document.getElementById('scan-jd-btn');
    const jdInput = document.getElementById('jd-input');
    const jdResults = document.getElementById('jd-results');
    const jdOutput = document.getElementById('jd-output');
    const suggestionsList = document.getElementById('suggestions-list');

    // Note: Dictionary now moved to Python backend.

    scanJdBtn.addEventListener('click', async () => {
        console.log('🔍 JD Scanner initialized');
        const text = jdInput.value.trim();
        if(!text) {
            alert('Please paste a job description first.');
            return;
        }

        scanJdBtn.disabled = true;
        scanJdBtn.innerHTML = '<i class="ph ph-spinner ph-spin"></i> Scanning...';

        try {
            console.log('📤 Sending request to API:', apiUrl('/api/jd/scan'), 'with text:', text.substring(0, 50) + '...');
            const formData = new FormData();
            formData.append('text', text);
            
            const response = await fetch(apiUrl('/api/jd/scan'), {
                method: 'POST',
                body: formData
            });
            
            console.log('📥 Response status:', response.status, response.statusText);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ HTTP Error:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const result = await response.json();
            console.log('✅ API Response:', result);
            
            if (!result.success) {
                throw new Error(result.error || 'API returned success=false');
            }
            
            if (result.success) {
                let suggestionsHTML = '';
                
                // Build suggestions from recommendations
                if (result.recommendations && result.recommendations.length > 0) {
                    result.recommendations.forEach(rec => {
                        suggestionsHTML += `
                            <div class="suggestion-card">
                                <p>${rec}</p>
                            </div>
                        `;
                    });
                } else {
                    suggestionsHTML = '<div class="alert alert-success">No significant bias detected. Good job!</div>';
                }
                
                jdOutput.innerHTML = result.processed_text;
                suggestionsList.innerHTML = suggestionsHTML;
                jdResults.classList.remove('hidden');
                
                const jdScoreCircle = document.getElementById('jd-score-circle');
                jdScoreCircle.textContent = result.bias_score;
                
                let circleClass = 'score-low';
                if(result.risk_level === 'High Risk') circleClass = 'score-high';
                else if(result.risk_level === 'Medium Risk') circleClass = 'score-medium';
                jdScoreCircle.className = `score-circle ${circleClass}`;
                
                document.getElementById('jd-risk-level').textContent = result.risk_level;
                if(result.risk_level === 'High Risk') document.getElementById('jd-risk-level').style.color = 'var(--danger-color)';
                else if(result.risk_level === 'Medium Risk') document.getElementById('jd-risk-level').style.color = 'var(--warning-color)';
                else document.getElementById('jd-risk-level').style.color = 'var(--success-color)';

                // Use direct per-category counts from API response
                document.getElementById('gb-count').textContent = result.gender_count || 0;
                document.getElementById('ab-count').textContent = result.age_count || 0;
                document.getElementById('db-count').textContent = result.disability_count || 0;
                document.getElementById('rb-count').textContent = result.religion_count || 0;
                document.getElementById('fb-count').textContent = result.family_count || 0;
                document.getElementById('pb-count').textContent = result.physical_count || 0;
                document.getElementById('seb-count').textContent = result.socio_economic_count || 0;
                document.getElementById('cb-count').textContent = result.cultural_count || 0;
                document.getElementById('hb-count').textContent = result.health_count || 0;
                document.getElementById('casteb-count').textContent = result.caste_count || 0;
                document.getElementById('appb-count').textContent = result.appearance_count || 0;

                // Display AI Audit Report if available
                const jdAiReportPanel = document.getElementById('jd-ai-report-panel');
                const jdAiReportContent = document.getElementById('jd-ai-report-content');
                if (jdAiReportPanel && jdAiReportContent && result.ai_report) {
                    jdAiReportContent.innerHTML = markdownToHtml(result.ai_report);
                    jdAiReportPanel.style.display = 'block';
                }

                // Display insights if available
                const jdInsightsList = document.getElementById('jd-insights-list');
                if (jdInsightsList && result.insights && result.insights.length > 0) {
                    jdInsightsList.innerHTML = result.insights.map(insight =>
                        `<li><i class="ph ph-info"></i> ${escapeHtml(insight)}</li>`
                    ).join('');
                    document.getElementById('jd-insights-panel').style.display = 'block';
                }
            }
        } catch (err) {
            console.error('❌ JD Scan Error:', err);
            console.error('Error stack:', err.stack);
            alert('Failed to scan job description.\n\nError: ' + (err.message || 'Unknown error') + '\n\nCheck console (F12) for details.');
        } finally {
            scanJdBtn.disabled = false;
            scanJdBtn.innerHTML = '<i class="ph ph-magnifying-glass"></i> Scan Complete';
        }
    });

    // -------------------------------------------------------------
    // MODE 3: Profile Simulator
    // -------------------------------------------------------------
    const simulateBtn = document.getElementById('simulate-btn');
    const simResultsCards = document.getElementById('sim-results-cards');

    simulateBtn.addEventListener('click', async () => {
        simulateBtn.disabled = true;
        simulateBtn.innerHTML = '<i class="ph ph-spinner ph-spin"></i> Running Counterfactuals...';

        const origGender = document.getElementById('sim-gender').value;
        const cfGender = document.getElementById('sim-gender-cf').value;
        const experience = document.getElementById('sim-experience').value || 4;
        const education = document.getElementById('sim-education').value || 'Bachelors';
        const scenario = document.getElementById('sim-scenario').value || 'Hiring';
        const ageGroup = document.getElementById('sim-age').value || '30-50';

        try {
            const formData = new FormData();
            formData.append('experience', experience);
            formData.append('education', education);
            formData.append('orig_gender', origGender);
            formData.append('cf_gender', cfGender);
            formData.append('scenario', scenario);
            formData.append('age_group', ageGroup);

            const response = await fetch(apiUrl('/api/profile/simulate'), {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'API returned success=false');
            }
            
            if (result.success) {
                document.getElementById('res-orig-gender').textContent = origGender;
                document.getElementById('res-cf-gender').textContent = cfGender;
                document.getElementById('exp-orig').textContent = origGender;
                document.getElementById('exp-cf').textContent = cfGender;
                
                // Get probabilities from direct result
                const origProb = result.orig_prob || 0;
                const cfProb = result.cf_prob || 0;
                const difference = Math.abs(result.difference) || 0;
                
                document.querySelector('.cf-card.original .cf-score').textContent = `${origProb.toFixed(1)}%`;
                document.querySelector('.cf-card.counterfactual .cf-score').textContent = `${cfProb.toFixed(1)}%`;
                
                const diffText = difference > 0 ? `+${difference.toFixed(1)}% difference` : `${difference.toFixed(1)}% difference`;
                document.querySelector('.bias-impact-alert p strong').textContent = diffText;
                const impactTitle = document.querySelector('.bias-impact-alert .alert strong');
                impactTitle.textContent = difference >= 15 ? 'Severe Bias Impact Detected' : (difference >= 5 ? 'Bias Impact Detected' : 'Minimal Bias Impact');
                
                // Render LLM Explanation
                const aiExplanationContainer = document.getElementById('sim-ai-explanation');
                if (aiExplanationContainer) {
                    aiExplanationContainer.textContent = result.llm_explanation || 'No explanation generated.';
                }
                
                // Render What-If Matrix (Counterfactual Grid)
                const matrixContainer = document.getElementById('sim-whatif-matrix');
                if (matrixContainer && result.cf_grid) {
                    matrixContainer.innerHTML = ''; // Clear previous
                    result.cf_grid.forEach(item => {
                        // Color scale for probabilities: <40=red, 40-70=yellow, >70=green
                        let badgeColor = '#dc3545'; // red
                        if (item.prob > 70) badgeColor = '#28a745'; // green
                        else if (item.prob >= 40) badgeColor = '#ffc107'; // yellow
                        
                        const textClass = item.prob >= 40 && item.prob <= 70 ? 'text-dark' : 'text-white';
                        
                        const cardHtml = `
                            <div style="background-color: var(--body-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 10px 15px; text-align: center; min-width: 120px; flex-grow: 1;">
                                <div class="text-muted small mb-1">${item.Gender} | ${item.Age}</div>
                                <span class="badge ${textClass}" style="background-color: ${badgeColor}; font-size: 1rem; padding: 6px 12px;">${item.prob.toFixed(1)}%</span>
                            </div>
                        `;
                        matrixContainer.innerHTML += cardHtml;
                    });
                }

                simResultsCards.classList.remove('hidden');
                document.querySelector('#simulator-results h3').style.opacity = '1';
                
                // Scroll to results
                document.getElementById('simulator-results').scrollIntoView({ behavior: 'smooth' });
            }
        } catch (err) {
            console.error('Simulation Error:', err);
            alert('Simulation failed: ' + (err.message || 'Unknown error'));
        } finally {
            simulateBtn.disabled = false;
            simulateBtn.innerHTML = 'Run Simulation';
        }
    });

    // -------------------------------------------------------------
    // Chatbot Logic
    // -------------------------------------------------------------
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbotClose = document.getElementById('chatbot-close');
    const chatbotPanel = document.getElementById('chatbot-panel');
    const chatbotInput = document.getElementById('chatbot-input-field');
    const chatbotSend = document.getElementById('chatbot-send');
    const chatbotMessages = document.getElementById('chatbot-messages');

    const toggleChatbot = () => chatbotPanel.classList.toggle('hidden');
    chatbotToggle.addEventListener('click', toggleChatbot);
    chatbotClose.addEventListener('click', toggleChatbot);

    chatbotSend.addEventListener('click', async () => {
        const text = chatbotInput.value.trim();
        if (!text) return;

        // Add user message
        chatbotMessages.innerHTML += `<div class="message user">${text}</div>`;
        chatbotInput.value = '';
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

        // Add typing indicator
        const typingId = 'typing-' + Date.now();
        chatbotMessages.innerHTML += `<div id="${typingId}" class="message ai"><i class="ph ph-spinner ph-spin"></i> Thinking...</div>`;
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

        try {
            const formData = new FormData();
            formData.append('message', text);

            const response = await fetch(apiUrl('/api/agent/chat'), {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            document.getElementById(typingId).remove();
            
            if (result.success) {
                // simple markdown to html for bold text
                let formattedReply = result.reply.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                chatbotMessages.innerHTML += `<div class="message ai">${formattedReply}</div>`;
            } else {
                chatbotMessages.innerHTML += `<div class="message ai">Error: ${result.error}</div>`;
            }
        } catch (err) {
            document.getElementById(typingId).remove();
            chatbotMessages.innerHTML += `<div class="message ai" style="color: var(--danger-color)">API connection failed. Make sure Backend is running.</div>`;
        }
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    });

    chatbotInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') chatbotSend.click();
    });
});
