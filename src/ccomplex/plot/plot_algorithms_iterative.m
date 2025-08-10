close all;
clearvars;

% Directorio de resultados (contiene subcarpetas topo_xxx/)
resultsDir = 'results_iterative';

% Lista de directorios topo_*
topoDirs = dir(fullfile(resultsDir, 'topo_*'));
numTopos = length(topoDirs);

% Prealocar
topoSizes = zeros(numTopos,1);
avgTimes  = zeros(numTopos,4); % columnas: Hops, lowLinksLoss, Power2Zero, Power2Zero+Links

% Nombres esperados de columnas (coinciden con los CSV que escribimos)
criteriaNames = {'Hops(s)', 'lowLinksLoss(s)', 'Power2Zero(s)', 'Power2Zero+Links(s)'};

for k = 1:numTopos
    fld = topoDirs(k).name;
    % extraer tamaño de la topología: topo_XXXX
    tok = regexp(fld, 'topo_(\d+)', 'tokens');
    if isempty(tok)
        warning('Nombre de carpeta no coincide con topo_NNN: %s. Se ignora.', fld);
        topoSizes(k) = NaN;
        avgTimes(k,:) = NaN;
        continue;
    end
    topoSizes(k) = str2double(tok{1}{1});
    
    % listar archivos run_*.csv dentro de la carpeta de la topología
    runFiles = dir(fullfile(resultsDir, fld, 'run_*.csv'));
    if isempty(runFiles)
        warning('No se han encontrado run_*.csv en %s. Se pone NaN.', fullfile(resultsDir,fld));
        avgTimes(k,:) = NaN;
        continue;
    end
    
    % matriz temporal para las medias por run (cada fila = un run, 4 columnas = criterios)
    runMeans = nan(length(runFiles), 4);
    
    for r = 1:length(runFiles)
        csvPath = fullfile(resultsDir, fld, runFiles(r).name);
        try
            T = readtable(csvPath);
        catch ME
            warning('Error leyendo %s : %s', csvPath, ME.message);
            continue;
        end
        
        % Comprobar que haya al menos 5 columnas (Delta + 4 criterios)
        if width(T) < 5
            warning('Fichero %s no tiene el formato esperado (menos de 5 columnas).', csvPath);
            continue;
        end
        
        % Tomamos las columnas 2:5 por defecto (ignoramos 'Delta')
        % Si el CSV tuviera distinto orden, intentar mapear por nombre:
        try
            data = T{:, 2:5}; % filas = deltas, cols = 4 criterios
        catch
            % intentar buscar por nombres
            cols = zeros(1,4);
            for c = 1:4
                idx = find(strcmp(T.Properties.VariableNames, criteriaNames{c}),1);
                if ~isempty(idx)
                    cols(c) = idx;
                else
                    cols(c) = NaN;
                end
            end
            if all(~isnan(cols))
                data = T{:, cols};
            else
                warning('No se han encontrado las 4 columnas esperadas en %s. Se omite este run.', csvPath);
                continue;
            end
        end
        
        % Comprobar no tener columnas all-NaN
        if all(all(isnan(data)))
            warning('Datos NaN en %s. Se omite este run.', csvPath);
            continue;
        end
        
        % media sobre las deltas (filas)
        runMeans(r, :) = mean(data, 1, 'omitnan');
    end
    
    % media entre runs (media de las medias de cada run) -> doble promedio
    valid = ~any(isnan(runMeans),2);
    if any(valid)
        avgTimes(k, :) = mean(runMeans(valid, :), 1, 'omitnan');
    else
        avgTimes(k, :) = NaN;
        warning('Todos los runs para %s fallaron o estaban mal formateados.', fld);
    end
end

% Eliminar entradas sin tamaño válido o sin datos
validTopos = ~isnan(topoSizes) & ~all(isnan(avgTimes),2);
topoSizes = topoSizes(validTopos);
avgTimes  = avgTimes(validTopos, :);

% Ordenar por tamaño
[topoSizes, ord] = sort(topoSizes);
avgTimes = avgTimes(ord, :);

% Preparar nombres y datos para plotting
algos   = {'Hops','lowLinksLoss','Power2Zero','Power2Zero+Links'};
markers = {'o-','s-','d-','^-'};
colors  = lines(4);

% Crear figura tipo 1x4
figure('Position',[100 100 1500 450]);
for i = 1:4
    ax = subplot(1,4,i);
    ax.FontSize = 12;
    y = avgTimes(:, i);
    
    % filtrar valores no positivos (no pueden entrar al log)
    valid_idx = ~isnan(y) & (y > 0);
    if sum(valid_idx) < 2
        warning('Pocos puntos válidos para %s: se mostrará vacío.', algos{i});
        plot(nan, nan); hold on;
        title(algos{i}, 'FontSize',14);
        xlabel('Graph size (nodes)', 'FontSize',12);
        if i==1, ylabel('Tiempo medio [s]', 'FontSize',12); end
        grid on;
        hold off;
        continue;
    end
    
    % Graficar datos medios (solo puntos válidos)
    p1 = plot(topoSizes(valid_idx), y(valid_idx), markers{2}, ...
              'MarkerSize',6, 'LineWidth',1, 'Color', [0.9290 0.6940 0.1250]);
    hold on;
    
    % Ajuste de regresión en log–log para obtener exponente y curva de regresión
    px = polyfit(log(topoSizes(valid_idx)), log(y(valid_idx)), 1);
    yfit = exp(polyval(px, log(topoSizes(valid_idx))));
    p2 = plot(topoSizes(valid_idx), yfit, ':', 'LineWidth',1.5, 'Color', 'k');
    
    % Etiquetas
    title(algos{i}, 'FontSize',14);
    xlabel('Graph size (nodes)', 'FontSize',12);
    if i == 1
        ylabel('Tiempo medio [s]', 'FontSize',12);
        h_analytical = p1; % para la leyenda global
        h_regression = p2;
    end
    
    grid on;
    
    % Anotación de la ley de potencia
    txt = sprintf('F(n)=n^{%.2f}', px(1));
    xlim([min(topoSizes) max(topoSizes)]);
    % ajustar ylim para que no se pise si hay outliers
    ymin = min(y(valid_idx));
    ymax = max(y(valid_idx));
    if ymin==ymax
        ylim([ymin*0.9 ymin*1.1]);
    else
        ylim([ymin*0.5 ymax*2]);
    end
    text(0.05, 0.9, txt, 'Units','normalized', 'FontSize',12);
    
    hold off;
end

% Leyenda común (Analytical values + Regression function) centrada abajo
lgd = legend([h_analytical, h_regression], ...
    {'Analytical values', 'Regression function'}, ...
    'Orientation', 'horizontal', 'FontSize', 12);

% Posicionar leyenda centrada abajo usando 'normalized'
lgd.Units = 'normalized';
% ajustar posición: [x y width height]
lgd.Position = [0.37, 0.02, 0.26, 0.05];

% Subir todos los subplots un poco para dejar sitio para la leyenda
offset = 0.08;  % más altura para evitar solape
scale = 0.93;   % escalar en altura cada subplot

allAxes = findall(gcf, 'Type', 'axes');
allAxes = flipud(allAxes);  % asegurar orden correcto izquierda-derecha
for a = 1:numel(allAxes)
    pos = allAxes(a).Position;
    pos(2) = pos(2) + offset;
    pos(4) = pos(4) * scale;
    allAxes(a).Position = pos;
end

% Exportar la figura a PDF vectorial
exportgraphics(gcf, fullfile(resultsDir,'iterative_regressions_4criteria.pdf'), 'ContentType','vector');
fprintf('Figura exportada a %s\n', fullfile(resultsDir,'iterative_regressions_4criteria.pdf'));
