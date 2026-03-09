import { useState } from "react";

const STAGES = [
  {
    id: "ingest",
    label: "1. VIDEO INGEST",
    icon: "\u{1F4E5}",
    color: "#2D6A4F",
    description: "Source video intake & audio extraction",
    tools: [
      {
        name: "FFmpeg",
        role: "Extract audio track from video, detect scene boundaries",
        pricing: "Free / open-source",
        costPer: "$0",
        notes: "Self-hosted, runs on your backend servers",
      },
      {
        name: "yt-dlp",
        role: "Download licensed/partnered YouTube content",
        pricing: "Free / open-source",
        costPer: "$0",
        notes: "Only for content you have rights to",
      },
    ],
    costEstimate: "$0 (compute only)",
  },
  {
    id: "transcribe",
    label: "2. TRANSCRIPTION",
    icon: "\u{1F4DD}",
    color: "#40916C",
    description: "Speech-to-text with speaker diarization & timestamps",
    tools: [
      {
        name: "OpenAI Whisper API",
        role: "Transcribe audio to text with word-level timestamps",
        pricing: "$0.006/min",
        costPer: "$0.36/hr",
        notes:
          "99 languages, best price-to-accuracy. Use GPT-4o Mini Transcribe at $0.003/min for budget option.",
      },
      {
        name: "Whisper (self-hosted)",
        role: "Same model, run on your own GPU",
        pricing: "~$276/mo fixed (GPU instance)",
        costPer: "Free after infra cost",
        notes: "Break-even at ~500+ hrs/month. Good for scale.",
      },
      {
        name: "ElevenLabs STT",
        role: "Alternative transcription within their ecosystem",
        pricing: "Billed per audio minute",
        costPer: "Included in dubbing credits",
        notes: "Convenient if already using ElevenLabs for TTS",
      },
    ],
    costEstimate: "~$0.36/hr of content",
  },
  {
    id: "translate",
    label: "3. TRANSLATION",
    icon: "\u{1F30D}",
    color: "#52B788",
    description: "Context-aware translation localized for children",
    tools: [
      {
        name: "Claude API (Anthropic)",
        role: "Cultural localization \u2014 rewrite scripts to feel native, adapt jokes, songs, cultural refs",
        pricing: "~$3/M input tokens, $15/M output tokens (Sonnet)",
        costPer: "~$0.02-0.05 per script page",
        notes:
          "Best for nuanced, child-appropriate rewrites. Use system prompts with cultural context.",
      },
      {
        name: "GPT-4o API (OpenAI)",
        role: "Alternative for translation with cultural adaptation",
        pricing: "~$2.50/M input, $10/M output",
        costPer: "~$0.02-0.04 per script page",
        notes:
          "Slightly cheaper, comparable quality for translation tasks",
      },
      {
        name: "DeepL API",
        role: "Fast, high-quality literal translation as a baseline",
        pricing: "$25/mo + $0.002/char overage",
        costPer: "~$20/M characters",
        notes:
          "Use as first pass, then refine with LLM for cultural adaptation",
      },
    ],
    costEstimate: "~$0.05-0.15 per video (5 min)",
  },
  {
    id: "tts",
    label: "4. VOICE SYNTHESIS",
    icon: "\u{1F399}\uFE0F",
    color: "#74C69D",
    description: "Generate expressive, kid-friendly dubbed audio",
    tools: [
      {
        name: "ElevenLabs Dubbing API",
        role: "End-to-end dubbing: transcribe \u2192 translate \u2192 voice clone \u2192 generate",
        pricing:
          "Creator: $22/mo (100K credits, ~50 min dubbing). Pro: $99/mo (~250 min). Scale: $330/mo (~1000 min)",
        costPer: "~$0.24-0.60/min depending on plan",
        notes:
          "Each output language billed separately. 10 min video \u00D7 3 languages = 30 min of credit. Best all-in-one option.",
      },
      {
        name: "ElevenLabs TTS API (\u00E0 la carte)",
        role: "Text-to-speech with voice cloning for individual character voices",
        pricing: "1 credit per character (Multilingual v2)",
        costPer: "Varies by plan tier",
        notes:
          "More control than dubbing API. Clone original character voices, adjust emotion/pace per line.",
      },
      {
        name: "OpenAI TTS",
        role: "Budget option for simpler voice generation",
        pricing: "$15/M characters (standard), $30/M (HD)",
        costPer: "~$0.015 per 1K chars",
        notes: "6 preset voices only, no cloning. Good for prototyping.",
      },
    ],
    costEstimate: "~$1.50-3.00 per 5-min video per language",
  },
  {
    id: "lipsync",
    label: "5. LIP-SYNC",
    icon: "\u{1F444}",
    color: "#95D5B2",
    description: "Match character mouth movements to new audio",
    tools: [
      {
        name: "Sync Labs (sync.so) API",
        role: "Studio-grade lip-sync for live-action, animation, and AI-generated video",
        pricing:
          "Creator: $29/mo (600 credits). Pro: $99/mo (2400 credits). 1 credit = 4 sec of video",
        costPer: "lipsync-2: $3/min, lipsync-2-pro: $5/min (via fal.ai)",
        notes:
          "Works on 2D animation, 3D, and live action. Best-in-class quality. YC-backed, founded by Wav2Lip creators.",
      },
      {
        name: "Rask.ai (all-in-one)",
        role: "Combined translation + dubbing + lip-sync in one platform",
        pricing:
          "Creator: $50/mo (25 min). Creator Pro: $120/mo (100 min + lip-sync). Business: $500/mo (500 min)",
        costPer: "Lip-sync uses 1 extra min per min of video",
        notes:
          "Convenient all-in-one but lip-sync quality reportedly weaker than Sync Labs. 135 languages supported.",
      },
      {
        name: "Wav2Lip (open-source)",
        role: "Self-hosted lip-sync model",
        pricing: "Free / open-source",
        costPer: "GPU compute cost only",
        notes:
          "Quality lower than commercial options but free. Good for MVP/testing.",
      },
    ],
    costEstimate: "~$15-25 per 5-min video",
  },
  {
    id: "compose",
    label: "6. COMPOSITION",
    icon: "\u{1F3AC}",
    color: "#B7E4C7",
    description: "Merge dubbed audio + lip-synced video + original music/SFX",
    tools: [
      {
        name: "FFmpeg",
        role: "Mux audio/video streams, overlay subtitles, adjust timing",
        pricing: "Free / open-source",
        costPer: "$0",
        notes:
          "Combine original background music/SFX (extracted in Step 1) with new dialogue track",
      },
      {
        name: "AWS MediaConvert",
        role: "Cloud-based encoding for multiple output formats (HLS, DASH)",
        pricing: "~$0.024/min (basic) for on-demand",
        costPer: "~$4.23 per 60-min video",
        notes: "Handles adaptive bitrate packaging for streaming",
      },
    ],
    costEstimate: "~$0-4 per video",
  },
  {
    id: "deliver",
    label: "7. DELIVERY & CDN",
    icon: "\u{1F4FA}",
    color: "#D8F3DC",
    description: "Store, stream, and serve to families worldwide",
    tools: [
      {
        name: "AWS S3 + CloudFront",
        role: "Object storage + global CDN for video delivery",
        pricing:
          "S3: $0.023/GB/mo storage. CloudFront: new flat-rate plans from $0/mo (free tier: 1TB transfer)",
        costPer: "~$0.085/GB data transfer (pay-as-you-go)",
        notes:
          "Free tier covers small-scale launch. S3 \u2192 CloudFront transfer is free.",
      },
      {
        name: "Cloudflare Stream",
        role: "Simpler alternative \u2014 upload and stream with built-in player",
        pricing:
          "$5/mo + $1 per 1K min of stored video + $1 per 1K min delivered",
        costPer: "~$0.001/min delivered",
        notes:
          "Much simpler than AWS. Good for MVP. Built-in player, no encoding needed.",
      },
      {
        name: "Mux",
        role: "Developer-friendly video API with analytics",
        pricing: "$0.007/min stored + $0.00016/min streamed",
        costPer: "Scales well for thousands of viewers",
        notes:
          "Great API, built-in analytics to track engagement per language",
      },
    ],
    costEstimate: "~$50-200/mo at early scale",
  },
];

const COST_SCENARIOS = [
  {
    label: "MVP / Validation",
    videos: 20,
    avgLength: 5,
    languages: 2,
    description: "20 videos \u00D7 5 min \u00D7 2 languages (Greek + Portuguese)",
    monthly: "$180 - $350",
    perVideo: "$9 - $17",
  },
  {
    label: "Early Product",
    videos: 100,
    avgLength: 5,
    languages: 5,
    description: "100 videos \u00D7 5 min \u00D7 5 languages",
    monthly: "$1,500 - $3,000",
    perVideo: "$3 - $6",
  },
  {
    label: "Growth Stage",
    videos: 500,
    avgLength: 5,
    languages: 10,
    description: "500 videos \u00D7 5 min \u00D7 10 languages",
    monthly: "$8,000 - $15,000",
    perVideo: "$1.60 - $3.00",
  },
];

const RECOMMENDED_STACK = [
  {
    category: "Backend / Orchestrator",
    pick: "FastAPI (Python)",
    why: "You already know this from the Maillard project. Orchestrate the pipeline as async jobs with Celery + Redis.",
    alt: "Node.js with BullMQ",
  },
  {
    category: "Transcription",
    pick: "OpenAI Whisper API ($0.006/min)",
    why: "Best cost-to-accuracy ratio. Supports 99 languages. No infrastructure needed. Upgrade to self-hosted at 500+ hrs/month.",
    alt: "Self-hosted Whisper on GPU",
  },
  {
    category: "Translation + Localization",
    pick: "Claude API (Sonnet) with cultural prompts",
    why: "Superior nuance for rewriting kids' content naturally. Build prompt templates per language that handle idioms, songs, humor adaptation.",
    alt: "DeepL for literal pass + GPT-4o for polish",
  },
  {
    category: "Voice Synthesis",
    pick: "ElevenLabs Scale Plan ($330/mo \u2192 1000 min)",
    why: "Best voice quality for kids' content. Voice cloning to match original characters. 32 language support. Dedicated dubbing API.",
    alt: "Rask.ai for all-in-one simplicity",
  },
  {
    category: "Lip-Sync",
    pick: "Sync Labs API (lipsync-2)",
    why: "Best-in-class quality. Works on animation AND live-action. Built by the original Wav2Lip researchers. $3/min via fal.ai.",
    alt: "Launch without lip-sync first to validate demand",
  },
  {
    category: "Video Delivery",
    pick: "Cloudflare Stream \u2192 Mux (at scale)",
    why: "Cloudflare Stream for MVP: simple, cheap, built-in player. Move to Mux when you need analytics and scale.",
    alt: "AWS S3 + CloudFront",
  },
  {
    category: "App / Frontend",
    pick: "React Native (mobile) + Next.js (web)",
    why: "Parents need a mobile app. Use React Native for iOS/Android, Next.js for web dashboard and content management.",
    alt: "Flutter for cross-platform",
  },
  {
    category: "Database",
    pick: "PostgreSQL + Redis",
    why: "Track content catalog, user preferences, language selections, processing jobs. Redis for job queues and caching.",
    alt: "Supabase for faster MVP",
  },
];

const LAUNCH_PHASES = [
  {
    time: "Week 1-2:",
    task: "Build pipeline prototype \u2014 transcribe \u2192 translate \u2192 dub 5 videos in Greek + Portuguese",
  },
  {
    time: "Week 3:",
    task: "Test with your daughter and 10 other multilingual families. Does she engage?",
  },
  {
    time: "Week 4:",
    task: "Add lip-sync to top 3 performing videos. A/B test engagement with vs. without",
  },
  {
    time: "Week 5-6:",
    task: "Partner with 5-10 Creative Commons / willing YouTube creators for content rights",
  },
  {
    time: "Week 7-8:",
    task: "Build parent-facing web app with language selector. Soft launch to 50 families",
  },
  {
    time: "Month 3:",
    task: "Based on data, decide: subscription product vs. B2B for bilingual schools",
  },
];

const COST_BREAKDOWN = [
  { label: "Transcription (Whisper)", cost: "$0.03" },
  {
    label: "Translation + Cultural Adaptation (Claude API)",
    cost: "$0.05 - $0.15",
  },
  { label: "Voice Synthesis (ElevenLabs)", cost: "$1.20 - $3.00" },
  { label: "Lip-Sync (Sync Labs)", cost: "$15.00 - $25.00" },
  { label: "Composition + Encoding", cost: "$0 - $0.50" },
];

export default function Pipeline() {
  const [activeStage, setActiveStage] = useState(null);
  const [activeTab, setActiveTab] = useState("pipeline");

  return (
    <div>
      {/* Sub-header */}
      <div style={{ marginBottom: 20 }}>
        <p
          style={{
            fontSize: 14,
            color: "#95D5B2",
            margin: 0,
            lineHeight: 1.6,
          }}
        >
          AI Kids' Content Dubbing Pipeline &mdash; multilingual video
          translation from source video to lip-synced, culturally-adapted
          content.
        </p>
      </div>

      {/* Tab Nav */}
      <div
        style={{
          display: "flex",
          gap: 4,
          marginBottom: 0,
        }}
      >
        {[
          { id: "pipeline", label: "Pipeline Stages" },
          { id: "costs", label: "Cost Scenarios" },
          { id: "recommended", label: "Recommended Stack" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 11,
              letterSpacing: 1.5,
              textTransform: "uppercase",
              padding: "10px 20px",
              border: "none",
              borderRadius: "8px 8px 0 0",
              cursor: "pointer",
              background: activeTab === tab.id ? "#1B4332" : "transparent",
              color: activeTab === tab.id ? "#95D5B2" : "#52B788",
              transition: "all 0.2s",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div>
        {/* Pipeline Tab */}
        {activeTab === "pipeline" && (
          <div
            style={{
              background: "#1B4332",
              borderRadius: "0 8px 8px 8px",
              padding: "32px",
              border: "1px solid #2D6A4F",
            }}
          >
            {/* Flow diagram */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                marginBottom: 32,
                overflowX: "auto",
                padding: "8px 0",
              }}
            >
              {STAGES.map((stage, i) => (
                <div
                  key={stage.id}
                  style={{ display: "flex", alignItems: "center" }}
                >
                  <button
                    onClick={() =>
                      setActiveStage(
                        activeStage === stage.id ? null : stage.id
                      )
                    }
                    style={{
                      background:
                        activeStage === stage.id ? stage.color : "#0B1D0F",
                      border: `2px solid ${stage.color}`,
                      borderRadius: 12,
                      padding: "12px 10px",
                      cursor: "pointer",
                      transition: "all 0.3s",
                      minWidth: 90,
                      textAlign: "center",
                      transform:
                        activeStage === stage.id ? "scale(1.08)" : "scale(1)",
                    }}
                  >
                    <div style={{ fontSize: 22, marginBottom: 4 }}>
                      {stage.icon}
                    </div>
                    <div
                      style={{
                        fontFamily: "'Space Mono', monospace",
                        fontSize: 8,
                        letterSpacing: 0.5,
                        color:
                          activeStage === stage.id ? "#D8F3DC" : "#95D5B2",
                        lineHeight: 1.3,
                      }}
                    >
                      {stage.label.split(". ")[1]}
                    </div>
                  </button>
                  {i < STAGES.length - 1 && (
                    <div
                      style={{
                        color: "#52B788",
                        fontSize: 18,
                        padding: "0 2px",
                        opacity: 0.6,
                      }}
                    >
                      &rarr;
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Stage details */}
            {activeStage ? (
              (() => {
                const stage = STAGES.find((s) => s.id === activeStage);
                return (
                  <div style={{ animation: "fadeIn 0.3s ease" }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        marginBottom: 8,
                      }}
                    >
                      <span style={{ fontSize: 28 }}>{stage.icon}</span>
                      <div>
                        <h2
                          style={{
                            fontFamily: "'Space Mono', monospace",
                            fontSize: 16,
                            margin: 0,
                            color: "#D8F3DC",
                          }}
                        >
                          {stage.label}
                        </h2>
                        <p
                          style={{
                            fontSize: 14,
                            color: "#95D5B2",
                            margin: "2px 0 0 0",
                          }}
                        >
                          {stage.description}
                        </p>
                      </div>
                    </div>

                    <div
                      style={{
                        background: "#0B1D0F",
                        borderRadius: 8,
                        padding: "4px 16px",
                        marginBottom: 16,
                        display: "inline-block",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "'Space Mono', monospace",
                          fontSize: 12,
                          color: "#74C69D",
                        }}
                      >
                        Est. cost: {stage.costEstimate}
                      </span>
                    </div>

                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 12,
                      }}
                    >
                      {stage.tools.map((tool, i) => (
                        <div
                          key={i}
                          style={{
                            background: "#0B1D0F",
                            borderRadius: 10,
                            padding: "16px 20px",
                            borderLeft: `3px solid ${stage.color}`,
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "flex-start",
                              flexWrap: "wrap",
                              gap: 8,
                              marginBottom: 8,
                            }}
                          >
                            <h3
                              style={{
                                fontFamily: "'Space Mono', monospace",
                                fontSize: 14,
                                margin: 0,
                                color: "#D8F3DC",
                              }}
                            >
                              {tool.name}
                            </h3>
                            <span
                              style={{
                                fontFamily: "'Space Mono', monospace",
                                fontSize: 11,
                                background: "#1B4332",
                                padding: "3px 10px",
                                borderRadius: 20,
                                color: "#74C69D",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {tool.costPer}
                            </span>
                          </div>
                          <p
                            style={{
                              fontSize: 13,
                              color: "#B7E4C7",
                              margin: "0 0 6px 0",
                              fontWeight: 500,
                            }}
                          >
                            {tool.role}
                          </p>
                          <p
                            style={{
                              fontSize: 12,
                              color: "#95D5B2",
                              margin: "0 0 6px 0",
                              fontStyle: "italic",
                            }}
                          >
                            Pricing: {tool.pricing}
                          </p>
                          <p
                            style={{
                              fontSize: 12,
                              color: "#74C69D",
                              margin: 0,
                              lineHeight: 1.5,
                              opacity: 0.85,
                            }}
                          >
                            {"\u{1F4A1}"} {tool.notes}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()
            ) : (
              <div
                style={{
                  textAlign: "center",
                  padding: "40px 20px",
                  color: "#52B788",
                  fontSize: 14,
                }}
              >
                {"\u261D\uFE0F"} Click any stage above to see tools, APIs, and
                cost details
              </div>
            )}
          </div>
        )}

        {/* Costs Tab */}
        {activeTab === "costs" && (
          <div
            style={{
              background: "#1B4332",
              borderRadius: "0 8px 8px 8px",
              padding: "32px",
              border: "1px solid #2D6A4F",
            }}
          >
            <h2
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 16,
                color: "#D8F3DC",
                margin: "0 0 8px 0",
              }}
            >
              Monthly Cost Scenarios
            </h2>
            <p
              style={{
                fontSize: 13,
                color: "#95D5B2",
                margin: "0 0 24px 0",
              }}
            >
              Estimates based on the recommended stack (ElevenLabs + Sync Labs +
              Claude API). Costs decrease significantly per video as you scale up
              plans.
            </p>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 16,
              }}
            >
              {COST_SCENARIOS.map((scenario, i) => (
                <div
                  key={i}
                  style={{
                    background: "#0B1D0F",
                    borderRadius: 12,
                    padding: "24px",
                    border: `1px solid ${i === 0 ? "#52B788" : "#2D6A4F"}`,
                    position: "relative",
                  }}
                >
                  {i === 0 && (
                    <div
                      style={{
                        position: "absolute",
                        top: -10,
                        right: 16,
                        background: "#52B788",
                        color: "#0B1D0F",
                        fontFamily: "'Space Mono', monospace",
                        fontSize: 9,
                        letterSpacing: 1.5,
                        textTransform: "uppercase",
                        padding: "3px 12px",
                        borderRadius: 20,
                        fontWeight: 700,
                      }}
                    >
                      Start Here
                    </div>
                  )}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      flexWrap: "wrap",
                      gap: 16,
                    }}
                  >
                    <div>
                      <h3
                        style={{
                          fontFamily: "'Space Mono', monospace",
                          fontSize: 15,
                          margin: "0 0 6px 0",
                          color: "#D8F3DC",
                        }}
                      >
                        {scenario.label}
                      </h3>
                      <p
                        style={{
                          fontSize: 13,
                          color: "#95D5B2",
                          margin: 0,
                        }}
                      >
                        {scenario.description}
                      </p>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div
                        style={{
                          fontFamily: "'Space Mono', monospace",
                          fontSize: 22,
                          fontWeight: 700,
                          color: "#74C69D",
                        }}
                      >
                        {scenario.monthly}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: "#52B788",
                          marginTop: 2,
                        }}
                      >
                        {scenario.perVideo} per video per language
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div
              style={{
                background: "#0B1D0F",
                borderRadius: 12,
                padding: "20px 24px",
                marginTop: 24,
                borderLeft: "3px solid #B7E4C7",
              }}
            >
              <h3
                style={{
                  fontFamily: "'Space Mono', monospace",
                  fontSize: 13,
                  color: "#D8F3DC",
                  margin: "0 0 10px 0",
                }}
              >
                {"\u{1F4B0}"} Cost Breakdown Per 5-Min Video
              </h3>
              <div
                style={{ fontSize: 13, color: "#B7E4C7", lineHeight: 2 }}
              >
                {COST_BREAKDOWN.map((item, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>{item.label}</span>
                    <span
                      style={{
                        fontFamily: "'Space Mono', monospace",
                        color: "#74C69D",
                      }}
                    >
                      {item.cost}
                    </span>
                  </div>
                ))}
                <div
                  style={{
                    borderTop: "1px solid #2D6A4F",
                    marginTop: 4,
                    paddingTop: 8,
                    display: "flex",
                    justifyContent: "space-between",
                    fontWeight: 700,
                  }}
                >
                  <span>TOTAL PER VIDEO PER LANGUAGE</span>
                  <span
                    style={{
                      fontFamily: "'Space Mono', monospace",
                      color: "#52B788",
                    }}
                  >
                    ~$16 - $29
                  </span>
                </div>
              </div>
              <p
                style={{
                  fontSize: 11,
                  color: "#52B788",
                  marginTop: 12,
                  marginBottom: 0,
                  lineHeight: 1.6,
                }}
              >
                {"\u26A0\uFE0F"} Lip-sync is the biggest cost driver. For MVP,
                consider launching voice-only dubbing first (~$1.50/video) and
                adding lip-sync as a premium feature. At scale, volume discounts
                from Sync Labs and ElevenLabs Enterprise can cut costs 40-60%.
              </p>
            </div>
          </div>
        )}

        {/* Recommended Stack Tab */}
        {activeTab === "recommended" && (
          <div
            style={{
              background: "#1B4332",
              borderRadius: "0 8px 8px 8px",
              padding: "32px",
              border: "1px solid #2D6A4F",
            }}
          >
            <h2
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 16,
                color: "#D8F3DC",
                margin: "0 0 24px 0",
              }}
            >
              Recommended MVP Stack
            </h2>

            {RECOMMENDED_STACK.map((item, i) => (
              <div
                key={i}
                style={{
                  background: "#0B1D0F",
                  borderRadius: 10,
                  padding: "18px 22px",
                  marginBottom: 12,
                  borderLeft: "3px solid #52B788",
                }}
              >
                <div
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: 10,
                    letterSpacing: 2,
                    color: "#52B788",
                    textTransform: "uppercase",
                    marginBottom: 4,
                  }}
                >
                  {item.category}
                </div>
                <h3
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "#D8F3DC",
                    margin: "0 0 6px 0",
                  }}
                >
                  &rarr; {item.pick}
                </h3>
                <p
                  style={{
                    fontSize: 13,
                    color: "#B7E4C7",
                    margin: "0 0 6px 0",
                    lineHeight: 1.5,
                  }}
                >
                  {item.why}
                </p>
                <p
                  style={{
                    fontSize: 11,
                    color: "#74C69D",
                    margin: 0,
                    opacity: 0.8,
                  }}
                >
                  Alternative: {item.alt}
                </p>
              </div>
            ))}

            <div
              style={{
                background: "#0B1D0F",
                borderRadius: 12,
                padding: "20px 24px",
                marginTop: 24,
                border: "2px solid #52B788",
              }}
            >
              <h3
                style={{
                  fontFamily: "'Space Mono', monospace",
                  fontSize: 14,
                  color: "#D8F3DC",
                  margin: "0 0 12px 0",
                }}
              >
                {"\u{1F680}"} Phase 1 Launch Plan
              </h3>
              <div
                style={{ fontSize: 13, color: "#B7E4C7", lineHeight: 2 }}
              >
                {LAUNCH_PHASES.map((phase, i) => (
                  <div key={i}>
                    <span
                      style={{ color: "#52B788", fontWeight: 700 }}
                    >
                      {phase.time}
                    </span>{" "}
                    {phase.task}
                  </div>
                ))}
              </div>
              <p
                style={{
                  fontSize: 12,
                  color: "#52B788",
                  marginTop: 12,
                  marginBottom: 0,
                  fontWeight: 500,
                }}
              >
                Estimated MVP budget: ~$500-800/month (API costs + hosting) +
                your development time
              </p>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
