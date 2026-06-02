module.exports = {
  apps: [
    {
      name: "flowzint-backend",
      script: "uvicorn",
      args: "app.main:app --host 127.0.0.1 --port 8000",
      cwd: "./backend",
      interpreter: "./backend/.venv/bin/python",
      instances: 1,
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
      autorestart: true,
      watch: false,
      env: {
        PORT: 3001,
        BACKEND_URL: "http://127.0.0.1:8000"
      }
    }
  ]
};
