import { http } from '@kit.NetworkKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { APIError, APIErrorCode } from './APIError';
import { hilog } from '@kit.PerformanceAnalysisKit';

export class APIClient {
  private static instance: APIClient;
  private baseURL: string = 'http://43.139.108.187:8001';
  private tag: string = 'APIClient';

  private constructor() {}

  public static getInstance(): APIClient {
    if (!APIClient.instance) {
      APIClient.instance = new APIClient();
    }
    return APIClient.instance;
  }

  public async fetch<T>(path: string, method: http.RequestMethod = http.RequestMethod.GET, extraData?: Object): Promise<T> {
    const url = path.startsWith('http') ? path : `${this.baseURL}${path}`;
    const httpRequest = http.createHttp();

    let contentType = 'application/json';
    if (typeof extraData === 'string') {
      contentType = 'application/x-www-form-urlencoded';
    }

    hilog.info(0x0000, this.tag, `Requesting: ${method} ${url}`);

    return new Promise((resolve, reject) => {
      httpRequest.request(url, {
        method: method,
        header: {
          'Content-Type': contentType
        },
        extraData: extraData,
        expectDataType: http.HttpDataType.OBJECT
      }, (err: BusinessError, data: http.HttpResponse) => {
        if (err) {
          hilog.error(0x0000, this.tag, `Request failed: ${err.message}`);
          reject(new APIError(APIErrorCode.NETWORK_ERROR, err.message));
          return;
        }

        if (data.responseCode === 401) {
          hilog.warn(0x0000, this.tag, 'Unauthorized access (401)');
          reject(new APIError(APIErrorCode.UNAUTHORIZED, 'Session expired'));
          return;
        }

        if (data.responseCode !== 200) {
          hilog.error(0x0000, this.tag, `Server error: ${data.responseCode}, response: ${JSON.stringify(data.result)}`);
          reject(new APIError(APIErrorCode.SERVER_ERROR, `Status code: ${data.responseCode}`));
          return;
        }

        // If it's a string (like from some APIs), try to parse it if expectDataType was OBJECT but it came as string? 
        // ArkUI handles OBJECT usually.
        resolve(data.result as T);
        httpRequest.destroy();
      });
    });
  }
}
