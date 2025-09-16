// OpenRouter API client for AI-powered video analysis

export interface OpenRouterConfig {
  apiKey: string
  baseUrl?: string
  model?: string
  timeout?: number
}

export interface AnalysisRequest {
  frames: Array<{
    imageData: string
    timestamp: string
    filename: string
  }>
  jobId: string
  options?: {
    detectVehicles?: boolean
    detectObstacles?: boolean
    detectWaste?: boolean
    confidenceThreshold?: number
  }
}

export interface AnalysisResponse {
  success: boolean
  error?: string
  analysis?: {
    incorrectParking: boolean
    wasteMaterial: boolean
    explanation: string
    frameDetails: any[]
    frames: any[]
    mitigationStrategies?: any[]
  }
}

export class OpenRouterClient {
  private config: Required<OpenRouterConfig>

  constructor(config: OpenRouterConfig) {
    this.config = {
      baseUrl: 'https://openrouter.ai/api/v1',
      model: 'openai/gpt-4o',
      timeout: 120000,
      ...config
    }
  }

  async analyzeFrames(request: AnalysisRequest): Promise<AnalysisResponse> {
    try {
      const messages = [
        {
          role: 'system',
          content: this.getSystemPrompt(request.options)
        },
        {
          role: 'user',
          content: this.buildUserContent(request.frames)
        }
      ]

      const response = await fetch(`${this.config.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.config.apiKey}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': 'https://warehouse-safety-portal.vercel.app',
          'X-Title': 'Warehouse Safety Inspector'
        },
        body: JSON.stringify({
          model: this.config.model,
          messages,
          max_tokens: 2000,
          temperature: 0.1,
          response_format: { type: 'json_object' }
        }),
        signal: AbortSignal.timeout(this.config.timeout)
      })

      if (!response.ok) {
        throw new Error(`OpenRouter API error: ${response.status} - ${response.statusText}`)
      }

      const result = await response.json()
      const analysis = JSON.parse(result.choices[0].message.content)

      return {
        success: true,
        analysis
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      }
    }
  }

  private getSystemPrompt(options?: AnalysisRequest['options']): string {
    return `You are a warehouse safety expert analyzing surveillance footage for potential hazards.

Analyze the provided warehouse/hallway images and identify safety violations that could:
1. Block emergency vehicle access
2. Impede evacuation routes
3. Create fire safety hazards
4. Violate OSHA warehouse safety standards

Focus on:
- Vehicles parked in hallways/emergency routes
- Large objects blocking pathways
- Waste or debris creating trip hazards
- Equipment improperly stored in walkways

For each detected issue, provide:
- Exact location using a 4x3 grid system (A1-A4, B1-B4, C1-C4)
- Severity level (critical, high, medium, low)
- Specific mitigation actions required
- Timeline for remediation

Respond in JSON format with detailed frame analysis and actionable recommendations.`
  }

  private buildUserContent(frames: AnalysisRequest['frames']): any[] {
    const content = [
      {
        type: 'text',
        text: `Analyze these ${frames.length} warehouse surveillance frames for safety hazards. Provide detailed analysis for each frame.`
      }
    ]

    frames.forEach(frame => {
      content.push({
        type: 'image_url',
        image_url: {
          url: `data:image/jpeg;base64,${frame.imageData}`
        }
      })
    })

    return content
  }

  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.config.baseUrl}/models`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.config.apiKey}`
        },
        signal: AbortSignal.timeout(5000)
      })
      return response.ok
    } catch {
      return false
    }
  }
}

export function createOpenRouterClient(apiKey: string): OpenRouterClient {
  return new OpenRouterClient({ apiKey })
}