const API_BASE = '';
let sessionId = localStorage.getItem('fb_session_id');
let currentPages = [];
let currentPageToken = null;

function switchPlatform(platform) {
    document.querySelectorAll('.platform-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));

    document.getElementById(`${platform}-platform`).classList.add('active');
    event.target.classList.add('active');
}

const Facebook = {
    async login() {
        try {
            const response = await fetch(`${API_BASE}/facebook/auth/login`);
            const data = await response.json();
            
            if (!response.ok) {
                showError(data.detail || 'Failed to initiate login');
                return;
            }
            
            window.location.href = data.login_url;
        } catch (error) {
            showError(`Failed to initiate login: ${error.message}`);
        }
    },

    async logout() {
        if (!sessionId) return;
        try {
            await fetch(`${API_BASE}/facebook/auth/logout/${sessionId}`, { method: 'POST' });
            localStorage.removeItem('fb_session_id');
            sessionId = null;
            updateAuthStatus(false);
        } catch (error) {
            showError('Logout failed');
        }
    },

    async checkStatus() {
        if (!sessionId) return false;
        try {
            const response = await fetch(`${API_BASE}/facebook/auth/status/${sessionId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.valid) {
                    updateAuthStatus(true, data);
                    await this.loadAdAccounts();
                    await this.Pages.getPages();
                    return true;
                }
            }
        } catch (error) {
            console.error('Status check failed:', error);
        }
        return false;
    },

    async loadAdAccounts() {
        try {
            const response = await fetch(`${API_BASE}/facebook/auth/accounts?session_id=${sessionId}`);
            const data = await response.json();

            const select = document.getElementById('ad-account-select');
            select.innerHTML = '<option value="">Select account...</option>';

            data.ad_accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = `${account.name} (${account.id})`;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load ad accounts:', error);
        }
    },

    Ads: {
        async getInsights() {
            const accountId = document.getElementById('ad-account-select').value;
            if (!accountId) {
                showError('Please select an ad account');
                return;
            }

            const resultsDiv = document.getElementById('ad-insights-results');
            resultsDiv.innerHTML = '<div class="loading">Loading insights...</div>';

            try {
                const response = await fetch(`${API_BASE}/facebook/insights/${accountId}?session_id=${sessionId}`);
                const data = await response.json();

                if (data.insights && data.insights.length > 0) {
                    resultsDiv.innerHTML = `
                        <div class="success">
                            <strong>Summary:</strong><br>
                            ${Object.entries(data.summary).map(([key, value]) =>
                        `<span class="metric"><strong>${key}:</strong> ${typeof value === 'number' ? value.toFixed(2) : value}</span>`
                    ).join('')}
                        </div>
                    `;
                } else {
                    resultsDiv.innerHTML = '<div class="error">No insights data available</div>';
                }
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">Failed to load insights: ${error.message}</div>`;
            }
        }
    },

    Pages: {
        async getPages() {
            const resultsDiv = document.getElementById('pages-results');
            resultsDiv.innerHTML = '<div class="loading">Loading pages...</div>';

            try {
                const response = await fetch(`${API_BASE}/facebook/pages?session_id=${sessionId}`);
                const data = await response.json();

                currentPages = data.pages || [];

                if (currentPages.length > 0) {
                    this.updatePageSelects(currentPages);

                    resultsDiv.innerHTML = `
                        <div class="success">
                            Found ${currentPages.length} page(s)
                        </div>
                        ${currentPages.map(page => `
                            <div class="result-item">
                                <strong>${page.name}</strong><br>
                                <small>Category: ${page.category || 'N/A'}</small>
                            </div>
                        `).join('')}
                    `;
                } else {
                    resultsDiv.innerHTML = '<div class="error">No pages found</div>';
                }
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">Failed to load pages: ${error.message}</div>`;
            }
        },

        updatePageSelects(pages) {
            const selects = ['page-select', 'posts-page-select'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                select.innerHTML = '<option value="">Select page...</option>';
                pages.forEach(page => {
                    const option = document.createElement('option');
                    option.value = JSON.stringify({ id: page.id, token: page.access_token });
                    option.textContent = page.name;
                    select.appendChild(option);
                });
            });
            document.getElementById('page-select-group').style.display = 'block';
        }
    },

    Posts: {
        async getPosts() {
            const selectValue = document.getElementById('posts-page-select').value;
            if (!selectValue) {
                showError('Please select a page');
                return;
            }

            const pageData = JSON.parse(selectValue);
            currentPageToken = pageData.token;

            const resultsDiv = document.getElementById('posts-results');
            resultsDiv.innerHTML = '<div class="loading">Loading posts...</div>';

            try {
                const response = await fetch(
                    `${API_BASE}/facebook/pages/${pageData.id}/posts?session_id=${sessionId}&page_token=${pageData.token}&limit=10`
                );
                const data = await response.json();

                if (data.posts && data.posts.length > 0) {
                    resultsDiv.innerHTML = `
                        <div class="success">Found ${data.total_posts} post(s)</div>
                        ${data.posts.map(post => `
                            <div class="post-card">
                                <div class="post-header">
                                    <small>${new Date(post.created_time).toLocaleString()}</small>
                                </div>
                                <p>${post.message || post.story || 'No content'}</p>
                                <button class="btn btn-secondary" onclick="Facebook.Posts.getInsights('${post.id}')">
                                    View Insights
                                </button>
                            </div>
                        `).join('')}
                    `;
                } else {
                    resultsDiv.innerHTML = '<div class="error">No posts found</div>';
                }
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">Failed to load posts: ${error.message}</div>`;
            }
        },

        async getInsights(postId) {
            const section = document.getElementById('post-insights-section');
            const content = document.getElementById('post-insights-content');

            section.classList.remove('hidden');
            content.innerHTML = '<div class="loading">Loading insights...</div>';
            section.scrollIntoView({ behavior: 'smooth' });

            try {
                const response = await fetch(
                    `${API_BASE}/facebook/posts/${postId}/insights?session_id=${sessionId}&page_token=${currentPageToken}`
                );
                const result = await response.json();

                if (result.success && result.data) {
                    const insights = result.data;
                    content.innerHTML = `
                        <div class="post-header">
                            <h4>${insights.message || 'Post'}</h4>
                            <small>${new Date(insights.created_time).toLocaleString()}</small>
                        </div>
                        
                        <div class="post-metrics">
                            <span class="metric"><strong>👍 Likes:</strong> ${insights.engagement.likes}</span>
                            <span class="metric"><strong>💬 Comments:</strong> ${insights.engagement.comments}</span>
                            <span class="metric"><strong>🔄 Shares:</strong> ${insights.engagement.shares}</span>
                            <span class="metric"><strong>❤️ Reactions:</strong> ${insights.engagement.reactions}</span>
                        </div>

                        ${Object.keys(insights.reactions_breakdown).length > 0 ? `
                            <h4 style="margin-top: 20px;">Reactions Breakdown</h4>
                            <div class="post-metrics">
                                ${Object.entries(insights.reactions_breakdown).map(([type, count]) =>
                        `<span class="metric">${getReactionEmoji(type)} ${count}</span>`
                    ).join('')}
                            </div>
                        ` : ''}

                        ${insights.permalink ? `
                            <button class="btn btn-secondary" onclick="window.open('${insights.permalink}', '_blank')">
                                View Post on Facebook
                            </button>
                        ` : ''}
                    `;
                } else {
                    content.innerHTML = '<div class="error">Failed to load insights</div>';
                }
            } catch (error) {
                content.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            }
        }
    }
};

function updateAuthStatus(connected, data = null) {
    const statusDiv = document.getElementById('auth-status');
    const featuresDiv = document.getElementById('facebook-features');
    const logoutBtn = document.getElementById('logout-btn');

    if (connected && data) {
        statusDiv.innerHTML = `
            <span class="status connected">Connected</span>
            <div style="margin-top: 10px;">
                <strong>${data.user_name}</strong><br>
                <small>${data.user_id}</small>
            </div>
        `;
        featuresDiv.classList.remove('hidden');
        logoutBtn.style.display = 'block';
    } else {
        statusDiv.innerHTML = '<span class="status disconnected">Not Connected</span>';
        featuresDiv.classList.add('hidden');
        logoutBtn.style.display = 'none';
    }
}

function showError(message) {
    alert(message);
}

function getReactionEmoji(type) {
    const emojis = {
        'like': '👍',
        'love': '❤️',
        'haha': '😆',
        'wow': '😮',
        'sad': '😢',
        'angry': '😠',
        'care': '🤗'
    };
    return emojis[type.toLowerCase()] || '👍';
}

async function checkConfiguration() {
    try {
        const response = await fetch(`${API_BASE}/config/check`);
        const config = await response.json();
        
        if (!config.ready) {
            const authCard = document.querySelector('#facebook-platform .card');
            const warning = document.createElement('div');
            warning.className = 'error';
            warning.innerHTML = '<strong>⚠️ Configuration Required</strong><br>Please set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET in .env file.<br>See SETUP.txt for instructions.';
            authCard.insertBefore(warning, authCard.firstChild);
        }
    } catch (error) {
        console.error('Failed to check configuration:', error);
    }
}

window.addEventListener('load', async () => {
    await checkConfiguration();
    
    const urlParams = new URLSearchParams(window.location.search);
    const callbackSessionId = urlParams.get('session_id');

    if (callbackSessionId) {
        localStorage.setItem('fb_session_id', callbackSessionId);
        sessionId = callbackSessionId;
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (sessionId) {
        await Facebook.checkStatus();
    }
});

