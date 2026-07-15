@{
    ModuleVersion     = '1.0.0'
    RootModule        = 'Hyper.Tools.psm1'
    GUID              = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
    Author            = 'welshDog'
    Description       = 'AI-callable PowerShell toolkit for HyperCode-V2.4. Registers BRO monitoring tools as PSAI agent functions.'
    PowerShellVersion = '7.0'
    FunctionsToExport = @(
        'Get-HyperConfig',
        'Get-HyperSecrets',
        'Get-HyperContainerHealth',
        'Restart-HyperContainer',
        'Get-HyperAgentStatus',
        'Get-HyperNemoclawHealth',
        'Get-HyperProcessHealth',
        'Get-HyperLogHits',
        'Send-HyperDiscordAlert',
        'Invoke-HyperHealthCheck'
    )
    PrivateData = @{
        PSData = @{
            Tags = @('HyperCode', 'PSAI', 'Monitoring', 'BRO', 'AI', 'Agents')
        }
    }
}
