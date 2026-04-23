export async function runAdminRequest(requestFn, fallbackMessage) {
  try {
    const { response, payload } = await requestFn();
    if (response && response.ok && payload && payload.success) {
      return { ok: true, data: payload.data, payload };
    }

    return {
      ok: false,
      message: (payload && payload.message) || fallbackMessage,
    };
  } catch (_) {
    return {
      ok: false,
      message: '网络异常，请检查后端服务是否已启动',
    };
  }
}
