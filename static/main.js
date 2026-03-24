document.addEventListener('DOMContentLoaded', () => {
    
    // DOM Elements
    const btnHealth = document.getElementById('btn-health');
    const btnPing = document.getElementById('btn-ping');
    const btnGet = document.getElementById('btn-get');
    const btnRefresh = document.getElementById('btn-refresh');
    const btnClearUser = document.getElementById('btn-clear-user');
    const btnClearAll = document.getElementById('btn-clear-all');
    const btnSaveUser = document.getElementById('btn-save-user');
    
    const inputUser = document.getElementById('input-user');
    const inputName = document.getElementById('input-name');
    const inputEmail = document.getElementById('input-email');
    
    const statusResult = document.getElementById('status-result');
    const kvResult = document.getElementById('kv-result');
    const saveResult = document.getElementById('save-result');

    // Helper to format output and show in result box
    const showResult = (boxElement, data, isError = false) => {
        if (typeof data !== 'string' && data.source) {
            // Cool visual indicator for the source
            const isRedis = data.source.toLowerCase().includes('redis');
            const color = isRedis ? '#10b981' : '#3b82f6';
            const bgColor = isRedis ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)';
            const badge = `<span style="float: right; margin-left: 10px; font-size: 0.75rem; padding: 4px 8px; border-radius: 6px; background: ${bgColor}; color: ${color}; border: 1px solid ${color}40; box-shadow: 0 0 10px ${color}20;">⚡ Source: ${data.source}</span>`;
            
            boxElement.innerHTML = `<div style="margin-bottom: 8px;">${badge}</div><pre style="margin: 0; white-space: pre-wrap; font-family: inherit;">${JSON.stringify(data, null, 2)}</pre>`;
        } else {
            boxElement.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
        }
        
        boxElement.classList.add('shown');
        if (isError) {
            boxElement.classList.add('error');
        } else {
            boxElement.classList.remove('error');
        }
    };

    // Generic fetch handler with UI feedback
    const fetchApi = async (url, resultBox, btnElement, originalText) => {
        try {
            // Loading state
            btnElement.textContent = 'Loading...';
            btnElement.disabled = true;
            resultBox.classList.remove('shown');

            const response = await fetch(url);
            const data = await response.json();
            
            showResult(resultBox, data, !response.ok);
        } catch (error) {
            showResult(resultBox, { error: 'Network error or server unreachable' }, true);
        } finally {
            // Restore button state
            btnElement.textContent = originalText;
            btnElement.disabled = false;
        }
    };

    // Event Listeners
    btnHealth.addEventListener('click', () => {
        fetchApi('/health', statusResult, btnHealth, 'Check Health');
    });

    btnPing.addEventListener('click', () => {
        fetchApi('/redis-test', statusResult, btnPing, 'Test Redis');
    });

    btnGet.addEventListener('click', () => {
        const userId = inputUser.value.trim();
        if (!userId) {
            showResult(kvResult, { error: 'User ID is required.' }, true);
            return;
        }
        fetchApi(`/user/${encodeURIComponent(userId)}`, kvResult, btnGet, 'Normal Fetch (Cache-Aside)');
    });

    btnRefresh.addEventListener('click', () => {
        const userId = inputUser.value.trim();
        if (!userId) {
            showResult(kvResult, { error: 'User ID is required.' }, true);
            return;
        }
        fetchApi(`/user/${encodeURIComponent(userId)}?refresh=true`, kvResult, btnRefresh, 'Force DB Refresh');
    });

    btnClearUser.addEventListener('click', () => {
        const userId = inputUser.value.trim();
        if (!userId) {
            showResult(kvResult, { error: 'User ID is required to clear its cache.' }, true);
            return;
        }
        fetchApi(`/clear-cache/${encodeURIComponent(userId)}`, kvResult, btnClearUser, 'Clear User Cache');
    });
    
    btnClearAll.addEventListener('click', () => {
        fetchApi(`/clear-all-cache`, kvResult, btnClearAll, 'Clear ALL Cache');
    });

    btnSaveUser.addEventListener('click', async () => {
        const name = inputName.value.trim();
        const email = inputEmail.value.trim();
        
        if (!name || !email) {
            showResult(saveResult, { error: 'Both Name and Email are required.' }, true);
            return;
        }

        try {
            btnSaveUser.textContent = 'Saving...';
            btnSaveUser.disabled = true;
            saveResult.classList.remove('shown');

            const response = await fetch('/user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, email })
            });
            const data = await response.json();
            
            showResult(saveResult, data, !response.ok);
            
            if (response.ok) {
                inputName.value = '';
                inputEmail.value = '';
                
                // If we know the user ID that was returned, we can prepopulate the lookup box
                if (data.user && data.user.id) {
                    inputUser.value = data.user.id;
                }
            }
        } catch (error) {
            showResult(saveResult, { error: 'Network error or server unreachable' }, true);
        } finally {
            btnSaveUser.textContent = 'Save User';
            btnSaveUser.disabled = false;
        }
    });
});
