# Usage Guide

This guide demonstrates how to effectively use the Educational AI Assistant, with examples showcasing the agentic capabilities.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Uploading Documents](#uploading-documents)
3. [Query Patterns](#query-patterns)
4. [Understanding Agent Behavior](#understanding-agent-behavior)
5. [Best Practices](#best-practices)
6. [Feature Examples](#feature-examples)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First-Time Setup

1. **Access the App**:
   - **Live Demo**: Visit [education-assistant-6smbo5cwjphtnc3qphcbkh.streamlit.app](https://education-assistant-6smbo5cwjphtnc3qphcbkh.streamlit.app/)
   - **Local**: Run `streamlit run app.py`

2. **Create Account**:
   - Click "Sign Up"
   - Enter username, email, password
   - Provide API keys (OpenAI & Pinecone required)

3. **Upload Your First Document**:
   - Navigate to "Documents" tab
   - Click "Upload PDF"
   - Select a PDF file from your device
   - Wait for processing confirmation

4. **Start Chatting**:
   - Go to "Chat" tab
   - Ask questions about your uploaded documents
   - Watch the agent work its magic!

---

## Uploading Documents

### Supported Formats

Currently supports: **PDF files only**

**Coming Soon**: DOCX, images (OCR), video transcripts

### Upload Process

```
1. Click "Documents" → "Upload PDF"
2. Select file (max ~50MB recommended)
3. System checks for duplicates (SHA-256 hash)
4. Text extraction (PyPDF2)
5. Chunking (2000 chars with 500 overlap)
6. Embedding generation (OpenAI ada-002)
7. Storage in Pinecone under your namespace
8. Success notification
```

**Processing Time**: ~1-2 seconds per page

### Managing Documents

**View Documents**:
```
Documents Tab → See list of uploaded files with timestamps
```

**Delete Documents**:
```
Documents Tab → Click "🗑️" next to filename → Confirm
```

> **Note**: Deletion removes vectors from Pinecone and metadata from database. This is **permanent**.

---

## Query Patterns

The agent autonomously selects tools based on your query. Here are effective patterns:

### 1. **Direct Questions**

**Pattern**: Ask specific questions about document content

**Examples**:
```
❓ "What is mitochondria according to my biology notes?"
❓ "How does the author define success in chapter 2?"
❓ "What are the main causes of the Civil War mentioned?"
```

**Agent Behavior**:
1. Calls `search_documents(query="mitochondria")`
2. Retrieves relevant chunks
3. Answers with citations: `[1] (biology_notes.pdf)`

---

### 2. **Summary Requests**

**Pattern**: Ask for condensed information

**Examples**:
```
📝 "Summarize the key points about photosynthesis"
📝 "Give me bullet points from chapter 5"
📝 "What are the main takeaways from my lecture notes?"
```

**Agent Behavior**:
1. Calls `search_documents(query="photosynthesis")`
2. Retrieves context chunks
3. Calls `summarize_text(retrieved_context)`
4. Returns bulleted summary

---

### 3. **Document-Specific Queries**

**Pattern**: Search within a particular file

**Examples**:
```
📄 "What does biology_chapter3.pdf say about enzymes?"
📄 "Search only lecture_notes.pdf for 'quantum mechanics'"
```

**Agent Behavior**:
- Calls `search_documents(query="enzymes", document="biology_chapter3.pdf")`
- Filters results to specified file

---

### 4. **Follow-Up Questions**

**Pattern**: Build on previous responses

**Examples**:
```
💬 User: "Tell me about the French Revolution"
🤖 Agent: [Provides detailed answer]

💬 User: "Summarize that in 3 points"
🤖 Agent: [Calls summarize_last_answer(max_points=3)]

💬 User: "Explain the second point more"
🤖 Agent: [Uses memory to understand context]
```

**Why This Works**: Agent has **conversational memory** (6 turns) and a tool to recall its own responses.

---

### 5. **List & Exploration**

**Pattern**: Discover what documents you have

**Examples**:
```
📚 "What documents do I have?"
📚 "List my uploaded files"
📚 "Show me all my notes"
```

**Agent Behavior**:
- Calls `list_documents()`
- Returns formatted list with timestamps

---

### 6. **Complex Multi-Step Queries**

**Pattern**: Questions requiring multiple tool calls

**Example**:
```
💬 "Compare what chapter 1 and chapter 3 say about evolution"
```

**Agent Behavior** (autonomous reasoning):
1. `search_documents(query="evolution", document="chapter1.pdf")`
2. `search_documents(query="evolution", document="chapter3.pdf")`
3. Synthesizes comparison from both results
4. Provides structured answer with citations

---

## Understanding Agent Behavior

### How the Agent Thinks

The agent follows this reasoning pattern:

```
┌─────────────────────────────────────────┐
│ 1. ANALYZE USER INTENT                  │
│    - What is the user asking for?       │
│    - Do I need context first?           │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 2. SELECT TOOL(S)                       │
│    - Need to search? → search_documents │
│    - Need to list? → list_documents     │
│    - Need to condense? → summarize_text │
│    - Recall prior answer? → summarize_  │
│      last_answer                        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 3. EXECUTE TOOL(S)                      │
│    - May call multiple tools in sequence│
│    - Each result informs next decision  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 4. SYNTHESIZE ANSWER                    │
│    - Ground response in retrieved data  │
│    - Include source citations           │
│    - Format for readability             │
└─────────────────────────────────────────┘
```

### Transparency

**See Tool Calls** (Local Development):
- Set `verbose=True` in `AgentExecutor` initialization
- Watch agent reasoning in console

**Example Output**:
```
> Entering new AgentExecutor chain...
Thought: I need to search documents to find information about photosynthesis
Action: search_documents
Action Input: {"query": "photosynthesis", "limit": 10}
Observation: [1] (biology_chapter2.pdf) Photosynthesis is the process...
Thought: I have relevant context. Now I'll answer the user.
Final Answer: Based on your biology notes, photosynthesis is...
```

---

## Best Practices

### Writing Effective Queries

✅ **DO**:
- Be specific: "What is the definition of X in chapter 2?"
- Use document names: "Search lecture_notes.pdf for Y"
- Ask for summaries explicitly: "Summarize the key points"
- Build on context: "Explain that second point more"

❌ **DON'T**:
- Be vague: "Tell me stuff"
- Ask about content not in documents: Agent will say "No relevant passages found"
- Expect real-time info: Agent only knows uploaded documents

### Document Organization

**Naming Convention**:
```
✅ Good:
   - biology_chapter1.pdf
   - lecture_2024-03-15.pdf
   - midterm_review_notes.pdf

❌ Confusing:
   - document.pdf
   - untitled.pdf
   - IMG_1234.pdf
```

**Why?** Clear names make document-specific queries easier:
- "What does biology_chapter1.pdf say about..." ✅
- "What does document.pdf say about..." ❓

---

## Feature Examples

### 1. Cited Responses

**Query**: "What is the scientific method?"

**Response**:
```
According to your documents, the scientific method involves:

1. Observation and Question Formation [1] (science_intro.pdf)
2. Hypothesis Development [1] (science_intro.pdf)
3. Experimentation and Data Collection [2] (lab_manual.pdf)
4. Analysis and Conclusion [2] (lab_manual.pdf)

The process is iterative, as noted in [3] (research_methods.pdf),
where findings may lead to new questions.
```

**Why Citations Matter**: You can trace answers back to source material.

---

### 2. Conversational Follow-Ups

**Conversation Flow**:
```
👤 "What are Newton's three laws of motion?"
🤖 [Provides detailed explanation with citations]

👤 "Give me that as a bullet list"
🤖 [Calls summarize_last_answer]
    • First Law: Object at rest stays at rest unless acted upon
    • Second Law: F = ma (Force equals mass times acceleration)
    • Third Law: Every action has equal and opposite reaction

👤 "Explain the second law with an example"
🤖 [Uses conversation memory]
    The second law (F = ma) means that force is proportional to 
    acceleration. For example, according to [1] (physics_notes.pdf),
    pushing a shopping cart (small mass) requires less force than...
```

---

### 3. Voice Synthesis (Optional)

If you've provided an ElevenLabs API key:

1. **Enable TTS**:
   - Settings → Toggle "Voice Output"

2. **Listen to Responses**:
   - After agent replies, click 🔊 "Play Audio"
   - Useful for studying while commuting

---

### 4. Feedback System

**Rate Responses**:
```
⭐⭐⭐⭐⭐ (5 stars)
💬 "Very helpful! Exactly what I needed."
```

**Why Provide Feedback?**
- Helps improve retrieval algorithms
- Identifies problematic responses
- Guides future features

---

### 5. Admin Audit Logs

**For Admins** (set via `ADMIN_USERS` env):

View audit trail:
```
Admin Tab → Audit Logs
- User 42 uploaded "chapter1.pdf" at 2024-03-15 10:23
- User 42 queried: "what is photosynthesis" at 2024-03-15 10:25
- User 42 deleted "old_notes.pdf" at 2024-03-15 10:30
```

**Use Cases**:
- Compliance tracking
- Usage analytics
- Debugging user issues

---

## Troubleshooting

### Issue: "No relevant passages found"

**Causes**:
1. Query doesn't match document content
2. Document not fully processed
3. Too specific query

**Solutions**:
- ✅ Rephrase query with broader terms
- ✅ Check Documents tab to confirm upload success
- ✅ Try: "List my documents" to verify content

---

### Issue: Agent gives generic answer (not citing sources)

**Cause**: Agent didn't retrieve context (shouldn't happen with proper system prompt)

**Solution**:
- Report this behavior (indicates bug)
- Try rephrasing: "Search my documents for X"

---

### Issue: Slow response times

**Causes**:
1. Large document corpus (many chunks to search)
2. Complex multi-step reasoning
3. API rate limits

**Solutions**:
- ✅ Delete old/unused documents
- ✅ Use document-specific queries to narrow search
- ✅ Check API key quotas (OpenAI/Pinecone)

---

### Issue: Upload fails

**Causes**:
1. File too large (>50MB)
2. Corrupted PDF
3. API key issues

**Solutions**:
- ✅ Split large PDFs into smaller files
- ✅ Try re-exporting the PDF
- ✅ Verify Pinecone & OpenAI keys in Settings

---

### Issue: Can't see other user's documents

**This is expected!** 

Each user operates in an **isolated namespace**. You can only access your own documents. This is a security feature, not a bug.

---

## API Key Management

### Updating Keys

```
Settings Tab → API Keys Section
→ Enter new key → Click "Update"
→ Keys are encrypted before storage
```

### Key Requirements

| Service | Required? | Purpose |
|---------|-----------|---------|
| OpenAI | ✅ Yes | Embeddings + Chat |
| Pinecone | ✅ Yes | Vector storage |
| ElevenLabs | ❌ Optional | Voice synthesis |

### Key Security

- ✅ Keys encrypted at rest (AES-256)
- ✅ Never logged or displayed
- ✅ Decrypted only in memory during session
- ⚠️ Master key (`APP_ENCRYPTION_KEY`) must be secured

---

## Advanced Usage

### Custom System Prompts (Future Feature)

**Planned**: Allow users to customize agent behavior

**Example Use Cases**:
- "Always provide answers in Spanish"
- "Focus on practical applications"
- "Use simple language for beginners"

### Multi-User Collaboration (Future Feature)

**Planned**: Share documents with team members

**Workflow**:
1. Upload document
2. Click "Share" → Enter collaborator's email
3. Collaborator can query shared documents
4. Maintain separate personal documents

---

## Getting Help

### Resources

- **Documentation**: [docs/ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- **Main README**: [../README.md](../README.md)

### Reporting Bugs

Use the **in-app feedback system** to report issues:

1. **Rate the problematic response** with ⭐ (1 star - lowest rating)
2. **Add a comment** describing the issue:
   - What you asked
   - What went wrong
   - What you expected

**Example Feedback**:
```
Rating: ⭐ (1 star)
Comment: "Asked about cellular respiration from biology_chapter1.pdf 
but agent gave generic answer without citing sources. Expected 
citations like [1] (biology_chapter1.pdf)."
```

This helps us identify and fix problems quickly. Your feedback is reviewed regularly to improve the system.

---

## Tips & Tricks

### 💡 Pro Tip 1: Batch Similar Questions

Instead of:
```
❌ "What is X?"
   [Wait for response]
   "What is Y?"
   [Wait for response]
   "What is Z?"
```

Try:
```
✅ "Explain X, Y, and Z from chapter 1"
```

Agent will retrieve context once and answer all three efficiently.

---

### 💡 Pro Tip 2: Use Document Names as Context

```
✅ "Compare what biology_ch1.pdf and biology_ch2.pdf say about DNA"
```

Agent understands to search both files separately.

---

### 💡 Pro Tip 3: Ask for Structure

```
✅ "Summarize chapter 3 in 5 bullet points"
✅ "Give me a table comparing X and Y"
✅ "List the steps for Z in order"
```

Agent will format accordingly.

---

### 💡 Pro Tip 4: Export Conversations

```
Chat Tab → "Export Transcript" → Download as TXT/PDF
```

Great for:
- Study notes
- Sharing with classmates
- Reviewing later

---

## Conclusion

The Educational AI Assistant is designed to help you learn more effectively by making your documents **queryable** and **conversational**. The agentic architecture means the system adapts to your needs rather than following rigid scripts.

**Key Takeaways**:
- ✅ Upload relevant documents first
- ✅ Ask specific, clear questions
- ✅ Use citations to verify information
- ✅ Provide feedback to improve the system
- ✅ Experiment with different query patterns

**Happy learning!** 🎓

---

**Need more help?** Check out:
- [Architecture Guide](ARCHITECTURE.md) - Technical deep dive
- [Main README](../README.md) - Setup and configuration
- [GitHub Issues](https://github.com/edebbyi/education-assistant/issues) - Report bugs or request features
