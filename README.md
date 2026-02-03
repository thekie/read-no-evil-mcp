# read-no-evil-mcp

A secure email gateway MCP server that protects AI agents from prompt injection attacks in emails.

## Overview

This MCP (Model Context Protocol) server provides a secure interface for AI agents to read emails while protecting against prompt injection attacks. It acts as a gateway between your email provider and AI assistants, scanning incoming messages for malicious content before they reach the agent.

## Features

- **Prompt Injection Detection**: Scans email content for prompt injection attempts using ML-based detection
- **IMAP Support**: Connects to any IMAP-compatible email provider
- **MCP Integration**: Exposes email functionality through the Model Context Protocol

## Installation

```bash
pip install read-no-evil-mcp
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

Configure the MCP server with your email credentials and add it to your MCP client configuration.

## Security

This project uses [ProtectAI's DeBERTa model](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) to detect and block prompt injection attempts in email content before they are processed by AI agents. The model runs locally using ONNX Runtime for efficient CPU inference.

## License

Apache-2.0
