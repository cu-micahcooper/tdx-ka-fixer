import { useState, useEffect, useCallback } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'

interface Props {
  initialContent: string
  onChange: (html: string) => void
}

function Btn({
  onClick,
  active,
  disabled,
  title,
  children,
}: {
  onClick: () => void
  active?: boolean
  disabled?: boolean
  title: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onMouseDown={e => { e.preventDefault(); onClick() }}
      title={title}
      disabled={disabled}
      className={`px-2 py-1 rounded text-sm font-medium border transition-colors disabled:opacity-40 ${
        active
          ? 'bg-slate-700 text-white border-slate-700'
          : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
      }`}
    >
      {children}
    </button>
  )
}

function Sep() {
  return <span className="w-px bg-slate-300 mx-1 self-stretch" />
}

export default function RichTextEditor({ initialContent, onChange }: Props) {
  const [htmlMode, setHtmlMode] = useState(false)
  const [rawHtml, setRawHtml] = useState(initialContent)

  const editor = useEditor({
    extensions: [
      StarterKit,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { class: 'text-blue-600 underline cursor-pointer' },
      }),
    ],
    content: initialContent,
    onUpdate({ editor }) {
      onChange(editor.getHTML())
    },
  })

  // Re-sync when initialContent changes (switching articles)
  useEffect(() => {
    if (editor && !htmlMode) {
      const current = editor.getHTML()
      if (initialContent !== current) {
        editor.commands.setContent(initialContent)
      }
    }
  }, [initialContent]) // eslint-disable-line react-hooks/exhaustive-deps

  const enterHtmlMode = useCallback(() => {
    if (!editor) return
    setRawHtml(editor.getHTML())
    setHtmlMode(true)
  }, [editor])

  const exitHtmlMode = useCallback(() => {
    if (!editor) return
    editor.commands.setContent(rawHtml)
    onChange(rawHtml)
    setHtmlMode(false)
  }, [editor, rawHtml, onChange])

  const setLink = useCallback(() => {
    if (!editor) return
    const previous = editor.getAttributes('link').href as string | undefined
    const url = window.prompt('URL (leave blank to remove link):', previous ?? '')
    if (url === null) return // cancelled
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
    } else {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
    }
  }, [editor])

  if (!editor) return null

  const dis = htmlMode // disable rich-text buttons while in HTML mode

  return (
    <div className="border border-slate-300 rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 px-3 py-2 bg-slate-50 border-b border-slate-200">
        <Btn onClick={() => editor.chain().focus().toggleBold().run()}
          active={editor.isActive('bold')} disabled={dis} title="Bold">
          <strong>B</strong>
        </Btn>
        <Btn onClick={() => editor.chain().focus().toggleItalic().run()}
          active={editor.isActive('italic')} disabled={dis} title="Italic">
          <em>I</em>
        </Btn>
        <Btn onClick={() => editor.chain().focus().toggleStrike().run()}
          active={editor.isActive('strike')} disabled={dis} title="Strikethrough">
          <s>S</s>
        </Btn>
        <Btn onClick={() => editor.chain().focus().toggleCode().run()}
          active={editor.isActive('code')} disabled={dis} title="Inline code">
          <code className="font-mono text-xs">`c`</code>
        </Btn>

        <Sep />

        {([1, 2, 3] as const).map(level => (
          <Btn key={level}
            onClick={() => editor.chain().focus().toggleHeading({ level }).run()}
            active={editor.isActive('heading', { level })} disabled={dis} title={`Heading ${level}`}>
            H{level}
          </Btn>
        ))}

        <Sep />

        <Btn onClick={() => editor.chain().focus().toggleBulletList().run()}
          active={editor.isActive('bulletList')} disabled={dis} title="Bullet list">
          • List
        </Btn>
        <Btn onClick={() => editor.chain().focus().toggleOrderedList().run()}
          active={editor.isActive('orderedList')} disabled={dis} title="Numbered list">
          1. List
        </Btn>
        <Btn onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          active={editor.isActive('codeBlock')} disabled={dis} title="Code block">
          <code className="font-mono text-xs">{'</>'}</code>
        </Btn>

        <Sep />

        <Btn onClick={setLink} active={editor.isActive('link')} disabled={dis} title="Insert / edit link">
          🔗 Link
        </Btn>
        {editor.isActive('link') && (
          <Btn onClick={() => editor.chain().focus().unsetLink().run()} disabled={dis} title="Remove link">
            ✕ Link
          </Btn>
        )}

        <Sep />

        <Btn onClick={() => editor.chain().focus().undo().run()} disabled={dis} title="Undo">↩</Btn>
        <Btn onClick={() => editor.chain().focus().redo().run()} disabled={dis} title="Redo">↪</Btn>

        <Sep />

        {/* HTML mode toggle */}
        <Btn
          onClick={htmlMode ? exitHtmlMode : enterHtmlMode}
          active={htmlMode}
          title={htmlMode ? 'Back to rich text' : 'Edit raw HTML'}
        >
          <code className="font-mono text-xs">&lt;/&gt; HTML</code>
        </Btn>
      </div>

      {/* Content area */}
      {htmlMode ? (
        <textarea
          value={rawHtml}
          onChange={e => setRawHtml(e.target.value)}
          spellCheck={false}
          className="w-full min-h-64 p-4 font-mono text-sm text-slate-800 bg-slate-950 text-green-400 focus:outline-none resize-y"
        />
      ) : (
        <EditorContent
          editor={editor}
          className="prose prose-sm max-w-none p-4 min-h-64 focus-within:outline-none bg-white [&_.ProseMirror]:outline-none"
        />
      )}
    </div>
  )
}
