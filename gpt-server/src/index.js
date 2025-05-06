#!/usr/bin/env node
"use strict";
/**
 * This is a template MCP server that implements a simple notes system.
 * It demonstrates core MCP concepts like resources and tools by allowing:
 * - Listing notes as resources
 * - Reading individual notes
 * - Creating new notes via a tool
 * - Summarizing all notes via a prompt
 */
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
/**
 * Simple in-memory storage for notes.
 * In a real implementation, this would likely be backed by a database.
 */
const notes = {
    "1": { title: "First Note", content: "This is note 1" },
    "2": { title: "Second Note", content: "This is note 2" }
};
/**
 * Create an MCP server with capabilities for resources (to list/read notes),
 * tools (to create new notes), and prompts (to summarize notes).
 */
const server = new index_js_1.Server({
    name: "ctrl_rafa",
    version: "0.1.0",
}, {
    capabilities: {
        resources: {},
        tools: {},
        prompts: {},
    },
});
/**
 * Handler for listing available notes as resources.
 * Each note is exposed as a resource with:
 * - A note:// URI scheme
 * - Plain text MIME type
 * - Human readable name and description (now including the note title)
 */
server.setRequestHandler(types_js_1.ListResourcesRequestSchema, () => __awaiter(void 0, void 0, void 0, function* () {
    return {
        resources: Object.entries(notes).map(([id, note]) => ({
            uri: `note:///${id}`,
            mimeType: "text/plain",
            name: note.title,
            description: `A text note: ${note.title}`
        }))
    };
}));
/**
 * Handler for reading the contents of a specific note.
 * Takes a note:// URI and returns the note content as plain text.
 */
server.setRequestHandler(types_js_1.ReadResourceRequestSchema, (request) => __awaiter(void 0, void 0, void 0, function* () {
    const url = new URL(request.params.uri);
    const id = url.pathname.replace(/^\//, '');
    const note = notes[id];
    if (!note) {
        throw new Error(`Note ${id} not found`);
    }
    return {
        contents: [{
                uri: request.params.uri,
                mimeType: "text/plain",
                text: note.content
            }]
    };
}));
/**
 * Handler that lists available tools.
 * Exposes a single "create_note" tool that lets clients create new notes.
 */
server.setRequestHandler(types_js_1.ListToolsRequestSchema, () => __awaiter(void 0, void 0, void 0, function* () {
    return {
        tools: [
            {
                name: "create_note",
                description: "Create a new note",
                inputSchema: {
                    type: "object",
                    properties: {
                        title: {
                            type: "string",
                            description: "Title of the note"
                        },
                        content: {
                            type: "string",
                            description: "Text content of the note"
                        }
                    },
                    required: ["title", "content"]
                }
            }
        ]
    };
}));
/**
 * Handler for the create_note tool.
 * Creates a new note with the provided title and content, and returns success message.
 */
server.setRequestHandler(types_js_1.CallToolRequestSchema, (request) => __awaiter(void 0, void 0, void 0, function* () {
    var _a, _b;
    switch (request.params.name) {
        case "create_note": {
            const title = String((_a = request.params.arguments) === null || _a === void 0 ? void 0 : _a.title);
            const content = String((_b = request.params.arguments) === null || _b === void 0 ? void 0 : _b.content);
            if (!title || !content) {
                throw new Error("Title and content are required");
            }
            const id = String(Object.keys(notes).length + 1);
            notes[id] = { title, content };
            return {
                content: [{
                        type: "text",
                        text: `Created note ${id}: ${title}`
                    }]
            };
        }
        default:
            throw new Error("Unknown tool");
    }
}));
/**
 * Handler that lists available prompts.
 * Exposes a single "summarize_notes" prompt that summarizes all notes.
 */
server.setRequestHandler(types_js_1.ListPromptsRequestSchema, () => __awaiter(void 0, void 0, void 0, function* () {
    return {
        prompts: [
            {
                name: "summarize_notes",
                description: "Summarize all notes",
            }
        ]
    };
}));
/**
 * Handler for the summarize_notes prompt.
 * Returns a prompt that requests summarization of all notes, with the notes' contents embedded as resources.
 */
server.setRequestHandler(types_js_1.GetPromptRequestSchema, (request) => __awaiter(void 0, void 0, void 0, function* () {
    if (request.params.name !== "summarize_notes") {
        throw new Error("Unknown prompt");
    }
    const embeddedNotes = Object.entries(notes).map(([id, note]) => ({
        type: "resource",
        resource: {
            uri: `note:///${id}`,
            mimeType: "text/plain",
            text: note.content
        }
    }));
    return {
        messages: [
            {
                role: "user",
                content: {
                    type: "text",
                    text: "Please summarize the following notes:"
                }
            },
            ...embeddedNotes.map(note => ({
                role: "user",
                content: note
            })),
            {
                role: "user",
                content: {
                    type: "text",
                    text: "Provide a concise summary of all the notes above."
                }
            }
        ]
    };
}));
/**
 * Start the server using stdio transport.
 * This allows the server to communicate via standard input/output streams.
 */
function main() {
    return __awaiter(this, void 0, void 0, function* () {
        const transport = new stdio_js_1.StdioServerTransport();
        yield server.connect(transport);
    });
}
main().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
});
