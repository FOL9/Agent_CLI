import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { messages, tasks } = await req.json();
    const apiKey = process.env.GROQ_API_KEY;

    if (!apiKey) {
      return NextResponse.json({ error: 'API key not found' }, { status: 500 });
    }

    const systemPrompt = `You are Lumina AI, a highly intelligent productivity assistant. 
    You help users manage their tasks and plan their day effectively.
    
    Current Tasks:
    ${tasks.map((t: any) => `- ${t.title} [${t.priority}] (${t.category})`).join('\n')}

    Your capabilities:
    1. Chat with the user about their goals and productivity.
    2. Suggest new tasks or modifications to existing ones.
    
    If you want to suggest adding tasks, include a special JSON block in your response like this:
    [COMMAND:ADD_TASKS]
    [
      {"title": "Task name", "priority": "high", "category": "Work"},
      ...
    ]
    [/COMMAND]

    Keep your conversational responses helpful, concise, and motivating.`;

    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'openai/gpt-oss-120b', // Keeping the user's preferred model
        messages: [
          { role: 'system', content: systemPrompt },
          ...messages
        ],
        temperature: 0.7,
      }),
    });

    const data = await response.json();
    const content = data.choices[0].message.content;

    return NextResponse.json({ content });
  } catch (error) {
    console.error('Chat API Error:', error);
    return NextResponse.json({ error: 'Failed to chat' }, { status: 500 });
  }
}
