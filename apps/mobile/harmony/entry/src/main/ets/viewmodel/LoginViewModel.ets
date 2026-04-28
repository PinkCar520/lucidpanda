import { APIClient } from '../network/APIClient';
import { AuthTokenStore } from '../common/AuthTokenStore';
import { LoginResponseDTO } from '../model/AuthModels';
import { common } from '@kit.AbilityKit';
import { http } from '@kit.NetworkKit';

export class LoginViewModel {
  private apiClient = APIClient.getInstance();
  private context: common.Context;

  constructor(context: common.Context) {
    this.context = context;
  }

  public async login(email: string, password: string): Promise<boolean> {
    try {
      // API expects form data for login usually (OAuth2 style)
      const formData = `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`;
      
      const response = await this.apiClient.fetch<LoginResponseDTO>(
        '/api/v1/auth/login',
        http.RequestMethod.POST,
        formData
      );

      const tokenStore = await AuthTokenStore.getInstance(this.context);
      await tokenStore.saveSession(
        response.access_token,
        response.refresh_token,
        response.expires_in
      );

      return true;
    } catch (error) {
      return false;
    }
  }
}
