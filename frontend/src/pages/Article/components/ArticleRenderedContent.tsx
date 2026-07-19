type Props = {
  html: string
}

export default function ArticleRenderedContent({ html }: Props) {
  return <div dangerouslySetInnerHTML={{ __html: html }} style={{ padding: '16px' }} />
}
