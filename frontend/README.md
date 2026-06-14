# Frontend Client

This is the Next.js React-based frontend application for the Cognitive Voice Intelligence Platform. It provides a secure user recording wizard interface for assessments and an interactive dashboard for clinicians.

---

## 🛠️ Requirements & Setup

Ensure you have **Node.js 18+** installed.

1.  **Install dependencies**:
    ```bash
    npm install
    ```
2.  **Configure Environment**:
    Create a local `.env.local` file from the `.env.example` template:
    ```bash
    cp .env.example .env.local
    ```
3.  **Launch the development server**:
    ```bash
    npm run dev
    ```
    Access the app at [http://localhost:3000](http://localhost:3000).

---

## 🏗️ Design System

*   **Styling**: Powered by **Tailwind CSS**.
*   **Components**: Built using **shadcn/ui** and **Lucide Icons** for clean, medical-grade interfaces.
*   **Recording Wizard**: Guides participants through the 3-question sequence, recording responses in high-quality mono audio format using the browser MediaRecorder API.
*   **Dashboard Visualizations**: Interactive stats displays and charts mapping lexical repeat structures, temporal timelines, and composite risk index dials.

---

## 📁 Repository Structure

```
frontend/
├── package.json            # Scripts and dependency lists
├── tsconfig.json           # TypeScript configuration
├── tailwind.config.js      # CSS styling configuration
├── postcss.config.js       # PostCSS plugins
├── .env.example            # Environment variables placeholder
├── README.md               # This documentation
└── src/
    ├── app/                # Next.js App Router (Layouts and Pages)
    │   ├── layout.tsx      # Global wrapper
    │   ├── page.tsx        # Homepage / Entry Portal
    │   ├── record/         # 3-step Assessment Wizard flow page
    │   └── dashboard/      # Clinician Results Dashboard page
    ├── components/         # Reusable UI Blocks (Buttons, Cards, Recording meters)
    ├── hooks/              # Custom hooks (e.g., useAudioRecorder)
    ├── lib/                # Utility modules (API fetching, tailwind merge)
    └── types/              # TypeScript typings
```
