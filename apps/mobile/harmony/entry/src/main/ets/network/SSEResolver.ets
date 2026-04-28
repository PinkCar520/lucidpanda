import { http } from '@kit.NetworkKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { util } from '@kit.ArkTS';
import { APIErrorCode, APIError } from './APIError';

export type SSECallback = (data: string) => void;

export class SSEResolver {
  private static instance: SSEResolver;
  private tag: string = 'SSEResolver';
  private activeRequests: Map<string, http.HttpRequest> = new Map();
  private decoder = util.TextDecoder.create('utf-8');

  private constructor() {}

  public static getInstance(): SSEResolver {
    if (!SSEResolver.instance) {
      SSEResolver.instance = new SSEResolver();
    }
    return SSEResolver.instance;
  }

  public subscribe(url: string, token: string | null, onData: SSECallback): string {
    const streamID = Math.random().toString(36).substring(7);
    const httpRequest = http.createHttp();
    
    this.activeRequests.set(streamID, httpRequest);

    const header: Record<string, string> = {
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache'
    };

    if (token) {
      header['Authorization'] = `Bearer ${token}`;
    }

    hilog.info(0x0000, this.tag, `Subscribing to SSE: ${url}`);

    httpRequest.on('dataReceive', (data: ArrayBuffer) => {
      const text = this.decoder.decodeWithStream(new Uint8Array(data));
      const lines = text.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const payload = line.substring(6).trim();
          if (payload) {
            onData(payload);
          }
        }
      }
    });

    httpRequest.request(url, {
      method: http.RequestMethod.GET,
      header: header,
      expectDataType: http.HttpDataType.ARRAY_BUFFER,
      readTimeout: 3600000 
    }, (err) => {
      if (err) {
        hilog.error(0x0000, this.tag, `SSE error for ${streamID}: ${err.message}`);
        this.stop(streamID);
      }
    });

    return streamID;
  }

  public stop(streamID: string) {
    const httpRequest = this.activeRequests.get(streamID);
    if (httpRequest) {
      httpRequest.off('dataReceive');
      httpRequest.destroy();
      this.activeRequests.delete(streamID);
      hilog.info(0x0000, this.tag, `SSE stopped: ${streamID}`);
    }
  }

  public stopAll() {
    this.activeRequests.forEach((req, id) => {
      this.stop(id);
    });
  }
}
