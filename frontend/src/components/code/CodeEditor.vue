<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { autocompletion } from '@codemirror/autocomplete'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { python } from '@codemirror/lang-python'
import { bracketMatching, foldGutter, indentOnInput } from '@codemirror/language'
import { EditorState } from '@codemirror/state'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView, drawSelection, highlightActiveLine, highlightActiveLineGutter, keymap, lineNumbers, placeholder as cmPlaceholder } from '@codemirror/view'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  disabled?: boolean
}>(), {
  placeholder: '在这里编写 Python 代码',
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editorHost = ref<HTMLElement | null>(null)
let editor: EditorView | null = null

onMounted(() => {
  if (!editorHost.value) return
  editor = new EditorView({
    parent: editorHost.value,
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        highlightActiveLine(),
        history(),
        drawSelection(),
        indentOnInput(),
        bracketMatching(),
        foldGutter(),
        autocompletion(),
        keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
        python(),
        oneDark,
        EditorView.lineWrapping,
        EditorView.editable.of(!props.disabled),
        EditorState.readOnly.of(props.disabled),
        cmPlaceholder(props.placeholder),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) emit('update:modelValue', update.state.doc.toString())
        }),
      ],
    }),
  })
})

watch(() => props.modelValue, (value) => {
  if (!editor || value === editor.state.doc.toString()) return
  editor.dispatch({
    changes: { from: 0, to: editor.state.doc.length, insert: value },
  })
})

onBeforeUnmount(() => {
  editor?.destroy()
  editor = null
})
</script>

<template>
  <div ref="editorHost" class="code-editor-host" />
</template>
