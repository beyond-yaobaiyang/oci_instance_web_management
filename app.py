from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_login import login_required
from flask_wtf.csrf import CSRFProtect, generate_csrf
import oci
import yaml
import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv
from instance_creator import OCIInstanceCreator
from auth import AuthManager, init_auth_routes
from oci_manager import get_oci_manager, OCIInstanceManager
from oci_resources import get_vcns, get_shapes, parse_tenants_config, get_subnets, get_network_security_groups, get_tenant_config
import re
import base64

# 加载 .env 文件
load_dotenv()

# 配置日志
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level.upper()))

def load_config():
    """
    加载配置，支持环境变量和配置文件
    优先级：环境变量 > 配置文件 > 默认配置
    """
    # 默认配置
    config = {
        'users': [
            {
                'username': 'admin',
                'password': 'admin123'
            }
        ],
        'tenants': [
            {
                'name': 'default_tenant',
                'regions': ['ap-chuncheon-1']
            }
        ]
    }
    
    try:
        # 尝试从配置文件加载
        config_path = os.environ.get('OCI_CONFIG_PATH', 'config.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                # 深度合并配置
                config['users'] = file_config.get('users', config['users'])
                config['tenants'] = file_config.get('tenants', config['tenants'])
    except Exception as e:
        logging.warning(f"配置文件加载失败，使用默认配置: {e}")
    
    # 环境变量覆盖（如果需要）
    # 目前保持原有逻辑，不做额外修改
    
    return config

# 全局配置
CONFIG = load_config()

# 配置日志
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(32)
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_CHECK_DEFAULT'] = True
app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'PATCH', 'DELETE']

# 初始化 CSRF 保护
csrf = CSRFProtect(app)

# 添加 CSRF 令牌生成的路由
@app.route('/get_csrf_token')
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})

# 配置 CSRF 豁免的路由
@csrf.exempt
def exempt_routes():
    return [
        'login',
        'static',
        'get_csrf_token'
    ]

# 在每个响应中添加 CSRF 令牌
@app.after_request
def add_csrf_token(response):
    response.headers['X-CSRFToken'] = generate_csrf()
    return response

# Initialize authentication
auth_manager = AuthManager()
login_manager = auth_manager.setup_login_manager(app)

# Initialize authentication routes
init_auth_routes(app, auth_manager)

# Initialize OCI manager
oci_manager = get_oci_manager(CONFIG['tenants'][0]['name'])  # 使用配置文件中存在的租户名

@app.route('/instances', methods=['GET'])
@login_required
def get_instances():
    try:
        tenant = request.args.get('tenant')
        region = request.args.get('region')
        
        if not tenant or not region:
            return jsonify({'error': '需要提供租户和区域信息'}), 400
            
        oci_manager = get_oci_manager(tenant)
        instances = oci_manager.list_instances(tenant, region)
        return jsonify(instances)
    except Exception as e:
        app.logger.error(f"获取实例列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/instance_details/<instance_id>')
@login_required
def get_instance_details(instance_id):
    try:
        tenant = request.args.get('tenant')
        region = request.args.get('region')
        
        if not tenant or not region:
            return jsonify({'error': '需要提供租户和区域信息'}), 400
            
        # 获取 OCI 配置
        config = get_tenant_config(tenant)
        if not config:
            return jsonify({'error': f'无法获取租户 {tenant} 的配置'}), 400
            
        # 更新区域
        config['region'] = region
        
        # 创建实例管理器
        instance_manager = OCIInstanceManager(config)
        
        # 获取实例详情
        instance = instance_manager.get_instance_details(tenant, region, instance_id)
        
        # 丰富实例详情
        instance['network_interfaces'] = instance_manager.get_network_interfaces(instance_id)
        
        return jsonify(instance)
    except Exception as e:
        logger.error(f"获取实例详情失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_instance', methods=['POST'])
@login_required
def delete_instance():
    try:
        tenant = request.form.get('tenant')
        region = request.form.get('region')
        instance_id = request.form.get('instance_id')
        
        if not all([tenant, region, instance_id]):
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400
            
        # 获取 OCI 配置
        config = get_tenant_config(tenant)
        if not config:
            return jsonify({
                'status': 'error',
                'message': f'无法获取租户 {tenant} 的配置'
            }), 400
            
        # 更新区域
        config['region'] = region
        
        # 创建实例管理器
        instance_manager = OCIInstanceManager(config)
        
        # 删除实例
        result = instance_manager.delete_instance(instance_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"删除实例时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/images', methods=['GET'])
@login_required
def list_images():
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        tenant_name = config['tenants'][0]['name']
        
        oci_manager = get_oci_manager(tenant_name)
        os_filter = request.args.get('os')
        images = oci_manager.list_images(os_filter)
        return jsonify(images)
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/manage_instance', methods=['POST'])
@login_required
def manage_instance():
    try:
        data = request.get_json()
        tenant_name = data.get('tenant')
        instance_id = data.get('instance_id')
        action = data.get('action')
        region = data.get('region')  
        
        if not all([tenant_name, instance_id, action]):
            return jsonify({
                'status': 'error', 
                'message': '缺少必要的参数'
            }), 400

        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        tenant_config = next((t for t in config['tenants'] if t['name'] == tenant_name), None)
        if not tenant_config:
            return jsonify({
                'status': 'error', 
                'message': f'未找到租户 {tenant_name}'
            }), 404

        oci_manager = get_oci_manager(tenant_name)

        result = oci_manager.manage_instance(
            instance_id=instance_id, 
            action=action,
            region=region
        )

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error managing instance: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/regions', methods=['GET'])
@login_required
def list_regions():
    """获取租户的可用区域列表"""
    try:
        tenant = request.args.get('tenant')
        if not tenant:
            return jsonify({'error': '缺少租户参数'}), 400
            
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        tenant_config = next(
            (t for t in config['tenants'] if t.get('name') == tenant),
            None
        )
        
        if not tenant_config:
            return jsonify({'error': f'找不到租户: {tenant}'}), 404
            
        regions = tenant_config.get('regions', [])
        if not regions:
            return jsonify({'error': '租户没有配置区域'}), 400
            
        region_list = []
        for region in regions:
            if isinstance(region, str):
                region_list.append({
                    'key': region,
                    'name': f"{region} Region"
                })
            else:
                region_list.append({
                    'key': region.get('key'),
                    'name': region.get('name', f"{region.get('key')} Region")
                })
                
        return jsonify(region_list)
        
    except Exception as e:
        logger.error(f"获取区域列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/config/tenants', methods=['GET'])
@login_required
def list_tenants():
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        tenants = config.get('tenants', [])
        return jsonify(tenants)
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/compartments', methods=['GET'])
@login_required
def list_compartments():
    try:
        tenant_name = request.args.get('tenant', 'c3198384906')  
        
        oci_manager = get_oci_manager(tenant_name)
        compartments = oci_manager.list_compartments()
        
        formatted_compartments = oci_manager._format_compartment_tree(compartments)
        
        return jsonify(formatted_compartments)
    except Exception as e:
        logger.error(f"Error listing compartments: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_tenants', methods=['GET'])
@login_required
def get_tenants():
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        tenants = parse_tenants_config(config)
        
        tenant_list = [
            {
                'name': tenant.get('name'),
                'display_name': tenant.get('display_name', tenant.get('name')),
                'compartment_id': tenant.get('compartment_id')
            } 
            for tenant in tenants
        ]
        
        return jsonify(tenant_list)
    except Exception as e:
        logger.error(f"获取租户列表失败: {e}")
        return jsonify([]), 500

@app.route('/get_regions', methods=['GET'])
@login_required
def get_regions():
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        tenants = parse_tenants_config(config)
        
        tenant_name = request.args.get('tenant')
        
        if not tenant_name:
            return jsonify([]), 400
        
        tenant_config = next((tenant for tenant in tenants if tenant.get('name') == tenant_name), None)
        
        if not tenant_config:
            return jsonify([]), 404
        
        regions = tenant_config.get('regions', [])
        
        region_list = [
            {
                'key': region if isinstance(region, str) else region.get('key', region),
                'name': f"{region} Region" if isinstance(region, str) else region.get('name', f"{region} Region"),
                'endpoint': f"https://{region}.oraclecloud.com" if isinstance(region, str) else region.get('endpoint', f"https://{region}.oraclecloud.com")
            }
            for region in regions
        ]
        
        if not region_list:
            region_list = [
                {
                    'key': 'us-ashburn-1',
                    'name': 'Ashburn, Virginia, USA',
                    'endpoint': 'https://us-ashburn-1.oraclecloud.com'
                }
            ]
        
        return jsonify(region_list)
    
    except Exception as e:
        logger.error(f"获取区域列表失败: {e}")
        return jsonify([]), 500

@app.route('/get_images', methods=['GET'])
@login_required
def get_images_list():
    try:
        tenant = request.args.get('tenant')
        region = request.args.get('region')
        os_type = request.args.get('os_type', '').lower()  
        
        images = get_oci_images(
            tenant_name=tenant, 
            region=region,
            os_type=os_type
        )
        
        return jsonify(images)
    except Exception as e:
        logger.error(f"获取镜像列表失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/get_shapes', methods=['GET'])
@login_required
def get_shapes():
    try:
        tenant = request.args.get('tenant')
        region = request.args.get('region')
        
        shapes = [
            'VM.Standard.A1.Flex',  
            'VM.Standard.E2.1.Micro'  
        ]
        
        return jsonify({
            'status': 'success',
            'shapes': shapes
        })
    
    except Exception as e:
        logger.error(f"获取实例形状失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get_shape_details', methods=['GET'])
@login_required
def get_shape_details_route():
    try:
        shape = request.args.get('shape')
        
        shape_details = {
            'VM.Standard.A1.Flex': {
                'name': 'VM.Standard.A1.Flex',
                'description': 'ARM 架构的灵活微型实例',
                'is_flex': True,
                'max_ocpus': 4,
                'max_memory_gb': 24
            },
            'VM.Standard.E2.1.Micro': {
                'name': 'VM.Standard.E2.1.Micro',
                'description': 'x86 架构的微型实例',
                'is_flex': False,
                'ocpus': 1,
                'memory_gb': 1
            }
        }
        
        if not shape:
            return jsonify({
                'status': 'error',
                'message': '未指定形状'
            }), 400
        
        details = shape_details.get(shape)
        if not details:
            return jsonify({
                'status': 'error',
                'message': '未找到指定形状的详细信息'
            }), 404
        
        return jsonify({
            'status': 'success',
            'details': details
        })
    
    except Exception as e:
        logger.error(f"获取形状详细信息失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get_availability_domains', methods=['GET'])
@login_required
def get_availability_domains():
    try:
        tenant_name = request.args.get('tenant')
        region = request.args.get('region')
        
        if not tenant_name or not region:
            return jsonify([]), 400
        
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        tenants = parse_tenants_config(config)
        
        tenant_config = next((tenant for tenant in tenants if tenant.get('name') == tenant_name), None)
        
        if not tenant_config:
            return jsonify([]), 404
        
        if tenant_name == 'zookejason' and region == 'ap-chuncheon-1':
            oci_config = {
                "user": tenant_config.get('user'),
                "key_file": tenant_config.get('key_file'),
                "fingerprint": tenant_config.get('fingerprint'),
                "tenancy": tenant_config.get('tenancy'),
                "region": region
            }
            
            logger.info(f"OCI Config for tenant {tenant_name}: {oci_config}")
            
            from oci.identity import IdentityClient
            import oci
            
            config_dict = {
                "user": oci_config["user"],
                "key_content": open(oci_config["key_file"], "r").read(),
                "fingerprint": oci_config["fingerprint"],
                "tenancy": oci_config["tenancy"],
                "region": oci_config["region"]
            }
            
            try:
                identity_client = IdentityClient(config_dict)
            except Exception as config_error:
                logger.error(f"配置创建失败: {config_error}", exc_info=True)
                return jsonify({"error": "OCI配置错误", "details": str(config_error)}), 500
            
            availability_domains = identity_client.list_availability_domains(
                compartment_id=tenant_config.get('tenancy')  
            ).data
            
            domains_list = [
                {
                    'id': ad.id,
                    'name': ad.name
                } 
                for ad in availability_domains
            ]
            
            return jsonify(domains_list)
        
        return jsonify([])
    
    except Exception as e:
        logger.error(f"获取可用域发生未知错误: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/get_vcns', methods=['GET'])
@login_required
def list_vcns():
    try:
        tenant_name = request.args.get('tenant')
        vcns = get_vcns(tenant_name)
        return jsonify(vcns)
    except Exception as e:
        logger.error(f"获取 VCN 列表失败: {e}")
        return jsonify([]), 500

@app.route('/get_subnets', methods=['GET'])
@login_required
def list_subnets():
    try:
        tenant_name = request.args.get('tenant')
        region = request.args.get('region')
        vcn_id = request.args.get('vcn_id')
        
        subnets = get_subnets(
            tenant_name=tenant_name, 
            region=region, 
            vcn_id=vcn_id
        )
        
        return jsonify(subnets)
    except Exception as e:
        logger.error(f"获取子网列表失败: {e}")
        return jsonify([]), 500

@app.route('/get_network_security_groups', methods=['GET'])
@login_required
def list_network_security_groups():
    try:
        tenant_name = request.args.get('tenant')
        region = request.args.get('region')
        vcn_id = request.args.get('vcn_id')
        
        nsgs = get_network_security_groups(
            tenant_name=tenant_name, 
            region=region, 
            vcn_id=vcn_id
        )
        
        return jsonify(nsgs)
    except Exception as e:
        logger.error(f"获取网络安全组列表失败: {e}")
        return jsonify([]), 500

@app.route('/start_instance', methods=['POST'])
@login_required
def start_instance():
    """启动实例"""
    try:
        tenant = request.form.get('tenant')
        region = request.form.get('region')
        instance_id = request.form.get('instance_id')
        
        if not all([tenant, region, instance_id]):
            return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
            
        try:
            oci_manager = get_oci_manager(tenant)
            if not oci_manager:
                return jsonify({'status': 'error', 'message': f'无法获取租户 {tenant} 的配置'}), 400
                
            # 更新区域
            oci_manager.config['region'] = region
            
            # 启动实例
            result = oci_manager.manage_instance(instance_id, 'start', region)
            
            if result:
                return jsonify({'status': 'success', 'message': '实例启动请求已发送'})
            else:
                return jsonify({'status': 'error', 'message': '启动实例失败'}), 500
                
        except Exception as e:
            logger.error(f"启动实例失败: {str(e)}")
            return jsonify({'status': 'error', 'message': f'启动实例失败: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"启动实例时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop_instance', methods=['POST'])
@login_required
def stop_instance():
    """停止实例"""
    try:
        tenant = request.form.get('tenant')
        region = request.form.get('region')
        instance_id = request.form.get('instance_id')
        
        if not all([tenant, region, instance_id]):
            return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
            
        try:
            oci_manager = get_oci_manager(tenant)
            if not oci_manager:
                return jsonify({'status': 'error', 'message': f'无法获取租户 {tenant} 的配置'}), 400
                
            # 更新区域
            oci_manager.config['region'] = region
            
            # 停止实例
            result = oci_manager.manage_instance(instance_id, 'stop', region)
            
            if result:
                return jsonify({'status': 'success', 'message': '实例停止请求已发送'})
            else:
                return jsonify({'status': 'error', 'message': '停止实例失败'}), 500
                
        except Exception as e:
            logger.error(f"停止实例失败: {str(e)}")
            return jsonify({'status': 'error', 'message': f'停止实例失败: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"停止实例时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/restart_instance', methods=['POST'])
@login_required
def restart_instance():
    """重启实例"""
    try:
        tenant = request.form.get('tenant')
        region = request.form.get('region')
        instance_id = request.form.get('instance_id')
        
        if not all([tenant, region, instance_id]):
            return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
            
        try:
            oci_manager = get_oci_manager(tenant)
            if not oci_manager:
                return jsonify({'status': 'error', 'message': f'无法获取租户 {tenant} 的配置'}), 400
                
            # 更新区域
            oci_manager.config['region'] = region
            
            # 重启实例
            result = oci_manager.manage_instance(instance_id, 'restart', region)
            
            if result:
                return jsonify({'status': 'success', 'message': '实例重启请求已发送'})
            else:
                return jsonify({'status': 'error', 'message': '重启实例失败'}), 500
                
        except Exception as e:
            logger.error(f"重启实例失败: {str(e)}")
            return jsonify({'status': 'error', 'message': f'重启实例失败: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"重启实例时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_oci_shapes(tenant_name=None, region=None, availability_domain=None):
    return [
        'VM.Standard.A1.Flex',  
        'VM.Standard.E2.1.Micro'  
    ]

def get_shape_details(tenant_name=None, region=None, shape=None):
    shape_details = {
        'VM.Standard.A1.Flex': {
            'name': 'VM.Standard.A1.Flex',
            'description': 'ARM 架构的灵活微型实例',
            'is_flex': True,
            'max_ocpus': 4,
            'max_memory_gb': 24
        },
        'VM.Standard.E2.1.Micro': {
            'name': 'VM.Standard.E2.1.Micro',
            'description': 'x86 架构的微型实例',
            'is_flex': False,
            'ocpus': 1,
            'memory_gb': 1
        }
    }
    
    return shape_details.get(shape)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)