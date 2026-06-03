module.exports = {
  apps: [
    {
      name: "flowzint-backend",
      script: "/home/azureuser/FLOWZINT/backend/.venv/bin/uvicorn",
      args: "app.main:app --host 127.0.0.1 --port 8000",
      cwd: "/home/azureuser/FLOWZINT/backend",
      instances: 1,
      exec_mode: "fork",
      interpreter: "none",
      autorestart: true,
      watch: false,
      env: {
        PORT: 8000
      }
    },
    {
      name: "flowzint-frontend",
      script: "npm",
      args: "run start",
      cwd: "./frontend",
      instances: 1,
      exec_mode: "fork",
      interpreter: "none",
      autorestart: true,
      watch: false,
      env: {
        PORT: 3000,
        NODE_ENV: "production"
      }
    },
    {
      name: "flowzint-whatsapp-bot",
      script: "bot.js",
      cwd: "./whatsapp-bot",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      env: {
        PORT: 3001,
        BACKEND_URL: "http://127.0.0.1:8000"
      }
    }
  ]
};
