export function getRecommendPreview(item) {
  const questionPayload =
    item && typeof item.question_payload === 'object' && item.question_payload !== null
      ? item.question_payload
      : {};
  const question = typeof questionPayload.question === 'string'
    ? questionPayload.question.trim()
    : '';
  const topic = typeof item?.recommended_topic === 'string'
    ? item.recommended_topic.trim()
    : '';

  return {
    title: question || topic || 'Untitled recommendation',
    meta: question ? topic : '',
  };
}
