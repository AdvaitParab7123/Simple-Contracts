/**
 * Pulse AI Assistant - Chatbot Widget
 */

class PulseAssistant {
    constructor() {
        this.isOpen = false;
        this.isLoading = false;
        this.messages = [];
        this.init();
    }

    init() {
        this.createWidget();
        this.attachEventListeners();
        this.addWelcomeMessage();
    }

    createWidget() {
        // Create container
        const container = document.createElement('div');
        container.id = 'pulse-assistant';
        container.innerHTML = `
            <!-- Chat Toggle Button -->
            <button class="chat-toggle" id="chatToggle" title="Chat with Pulse AI">
                <i class="bi bi-chat-dots-fill chat-icon"></i>
                <i class="bi bi-x-lg close-icon"></i>
            </button>

            <!-- Chat Window -->
            <div class="chat-window" id="chatWindow">
                <div class="chat-header">
                    <div class="chat-header-info">
                        <div class="chat-avatar">
                            <i class="bi bi-stars"></i>
                        </div>
                        <div>
                            <div class="chat-title">Pulse Assistant</div>
                            <div class="chat-status">AI-powered help</div>
                        </div>
                    </div>
                    <button class="chat-minimize" id="chatMinimize">
                        <i class="bi bi-dash-lg"></i>
                    </button>
                </div>

                <div class="chat-messages" id="chatMessages">
                    <!-- Messages will be inserted here -->
                </div>

                <div class="chat-input-area">
                    <div class="quick-actions" id="quickActions">
                        <button class="quick-action" data-message="How do I create a new contract?">Create contract</button>
                        <button class="quick-action" data-message="What are the different contract statuses?">Contract statuses</button>
                        <button class="quick-action" data-message="How do approvals work?">Approvals</button>
                    </div>
                    <form class="chat-form" id="chatForm">
                        <input type="text" 
                               class="chat-input" 
                               id="chatInput" 
                               placeholder="Ask me anything..."
                               autocomplete="off">
                        <button type="submit" class="chat-send" id="chatSend">
                            <i class="bi bi-send-fill"></i>
                        </button>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(container);

        // Store references
        this.toggle = document.getElementById('chatToggle');
        this.window = document.getElementById('chatWindow');
        this.messages_container = document.getElementById('chatMessages');
        this.form = document.getElementById('chatForm');
        this.input = document.getElementById('chatInput');
        this.minimize = document.getElementById('chatMinimize');
        this.quickActions = document.getElementById('quickActions');
    }

    attachEventListeners() {
        // Toggle chat
        this.toggle.addEventListener('click', () => this.toggleChat());
        this.minimize.addEventListener('click', () => this.toggleChat());

        // Send message
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Quick actions
        this.quickActions.querySelectorAll('.quick-action').forEach(btn => {
            btn.addEventListener('click', () => {
                const message = btn.dataset.message;
                this.input.value = message;
                this.sendMessage();
            });
        });

        // Close on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.toggleChat();
            }
        });
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        this.toggle.classList.toggle('open', this.isOpen);
        this.window.classList.toggle('open', this.isOpen);
        
        if (this.isOpen) {
            this.input.focus();
            // Hide quick actions if there are messages
            if (this.messages.length > 1) {
                this.quickActions.style.display = 'none';
            }
        }
    }

    addWelcomeMessage() {
        this.addMessage('assistant', `Hi! I'm your Pulse Assistant. I can help you with:

• **Navigating the platform** - Find features and pages
• **Contract questions** - Create, edit, manage contracts
• **Approvals & workflows** - Understand the process
• **General guidance** - Best practices and tips

How can I help you today?`);
    }

    addMessage(role, content) {
        this.messages.push({ role, content });
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        
        const avatar = role === 'assistant' 
            ? '<div class="message-avatar"><i class="bi bi-stars"></i></div>'
            : '';
        
        // Convert markdown-style bold to HTML
        const formattedContent = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = `
            ${avatar}
            <div class="message-content">${formattedContent}</div>
        `;
        
        this.messages_container.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addLoadingMessage() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'chat-message assistant loading';
        loadingDiv.id = 'loadingMessage';
        loadingDiv.innerHTML = `
            <div class="message-avatar"><i class="bi bi-stars"></i></div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        this.messages_container.appendChild(loadingDiv);
        this.scrollToBottom();
    }

    removeLoadingMessage() {
        const loading = document.getElementById('loadingMessage');
        if (loading) loading.remove();
    }

    scrollToBottom() {
        this.messages_container.scrollTop = this.messages_container.scrollHeight;
    }

    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isLoading) return;

        // Hide quick actions after first message
        this.quickActions.style.display = 'none';

        // Add user message
        this.addMessage('user', message);
        this.input.value = '';
        
        // Show loading
        this.isLoading = true;
        this.addLoadingMessage();

        try {
            const response = await fetch('/contracts/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    message: message,
                    history: this.messages.slice(-10) // Send last 10 messages for context
                })
            });

            const data = await response.json();
            
            this.removeLoadingMessage();
            
            if (data.success) {
                this.addMessage('assistant', data.response);
            } else {
                this.addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
            }
        } catch (error) {
            console.error('Chat error:', error);
            this.removeLoadingMessage();
            this.addMessage('assistant', 'Sorry, I\'m having trouble connecting. Please try again later.');
        }

        this.isLoading = false;
    }

    getCSRFToken() {
        const cookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.pulseAssistant = new PulseAssistant();
});

